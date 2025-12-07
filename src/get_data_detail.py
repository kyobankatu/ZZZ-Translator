from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import time
import os
import re
import json
import sys
import yaml
import google.generativeai as genai
from tqdm import tqdm

# キャラクター一覧ページ (英語版でIDを取得するのが無難)
CHAR_LIST_URL = "https://wiki.hoyolab.com/pc/zzz/aggregate/8?lang=en-us"

# 設定ファイルから出力先を読み込む
try:
    with open("resource/data.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    OUTPUT_FILE = config.get("detail_output", "resource/zzz_glossary_detail.csv")
except Exception as e:
    print(f"Warning: Could not load data.yml, using default path. Error: {e}")
    OUTPUT_FILE = "resource/zzz_glossary_detail.csv"

def get_character_entry_ids(browser):
    """
    キャラクター一覧ページから全キャラクターのEntry IDを取得する
    """
    print(f"Fetching character list from {CHAR_LIST_URL}...")
    page = browser.new_page()
    page.goto(CHAR_LIST_URL, wait_until="networkidle", timeout=60000)
    
    # 無限スクロール対応: ページ最下部までスクロール
    last_height = page.evaluate("document.body.scrollHeight")
    while True:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        print("  Scrolling...")

    # キャラクターカードを取得
    grid_selector = "div.tw-grid.tw-gap-y-4.tw-grid-cols-2.tw-gap-x-7"
    item_selector = "div.tw-relative.tw-flex.tw-p-4.tw-rounded-2xl.tw-bg-gt-g-grey-black-2.tw-cursor-pointer"
    card_selector = f"{grid_selector} > {item_selector}"
    
    cards = page.locator(card_selector)
    count = cards.count()
    print(f"  Found {count} character cards.")
    
    entry_ids = []
    card_handles = cards.element_handles()
    
    for i, handle in enumerate(card_handles):
        try:
            # Ctrl(Meta)+Click で新しいタブで開き、URLからIDを取得する
            with page.context.expect_page() as new_page_info:
                modifier = "Meta" if os.name == 'posix' else "Control"
                handle.click(modifiers=[modifier])
            
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            
            # URLからID抽出 (https://wiki.hoyolab.com/pc/zzz/entry/909)
            url = new_page.url
            match = re.search(r'/entry/(\d+)', url)
            if match:
                entry_id = match.group(1)
                entry_ids.append(entry_id)
                print(f"  [{i+1}/{count}] Found ID: {entry_id}")
            
            new_page.close()
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error processing card {i}: {e}")
            continue

    page.close()
    return list(set(entry_ids))

def extract_mindscape_from_html(html_content):
    """心象映画 (Mindscape Cinema) のデータを静的HTMLから抽出する"""
    soup = BeautifulSoup(html_content, "html.parser")
    extracted_items = []

    mindscape_section = soup.find(id="4_summaryList")
    
    if mindscape_section:
        items = mindscape_section.select(".list_XeCAT .item_BL74W")
        for item in items:
            name_div = item.select_one(".name_ddrhh")
            title = name_div.text.strip() if name_div else "Unknown"

            desc_div = item.select_one(".ProseMirror")
            if desc_div:
                description = desc_div.get_text(separator=" ", strip=True)
                extracted_items.append({
                    "type": "MindscapeDesc", 
                    "title": title,
                    "value": description
                })

    return extracted_items

def extract_skills_interactively(page):
    """スキルセクションを操作してデータを抽出する"""
    extracted_items = []
    skill_section_selector = "[id='3_agent_talent']"

    try:
        page.wait_for_selector(skill_section_selector, state="attached", timeout=10000)
        page.locator(skill_section_selector).scroll_into_view_if_needed()
        time.sleep(2)
    except Exception as e:
        return extracted_items

    icons = page.locator(f"{skill_section_selector} .iconContainer_i31U6")
    icon_count = icons.count()
    
    print(f"  Found {icon_count} skill icons.")

    for i in range(icon_count):
        try:
            # アイコン要素を取得し、JSで直接クリックイベントを発火させる
            icon = icons.nth(i)
            icon.scroll_into_view_if_needed()
            icon.evaluate("el => el.click()")
            
            time.sleep(1.0)

            tabs = page.locator(f"{skill_section_selector} .home-common-module-tabs-item")
            tab_count = tabs.count()
            
            # print(f"    Skill {i+1}: Found {tab_count} tabs")

            loop_range = range(tab_count) if tab_count > 0 else range(1)

            for j in loop_range:
                if tab_count > 0:
                    tab = tabs.nth(j)
                    tab.scroll_into_view_if_needed()
                    tab.evaluate("el => el.click()")
                    time.sleep(0.5)

                content_area = page.locator(f"{skill_section_selector} .tw-overflow-hidden.tw-rounded-xl")
                
                title_locator = content_area.locator(".tw-text-lg-pc").first
                if title_locator.count() > 0:
                    title = title_locator.text_content().strip()
                else:
                    title = f"Skill_{i}_{j}"

                desc_locator = content_area.locator(".ProseMirror").first
                if desc_locator.count() > 0:
                    description = desc_locator.inner_text().replace("\n", " ")
                    extracted_items.append({
                        "type": "SkillDesc",
                        "skill_idx": i,
                        "tab_idx": j,
                        "title": title,
                        "value": description
                    })
        except Exception as e:
            print(f"    Error extracting skill {i}-{j}: {e}")

    return extracted_items

def extract_terms_batch_with_ai(model, pairs_batch):
    """
    複数の日英テキストペアから用語を一括抽出する (バッチ処理)
    pairs_batch: [{"en_title":..., "en_desc":..., "ja_title":..., "ja_desc":...}, ...]
    """
    # 入力データをJSON文字列化してプロンプトに埋め込む
    input_json = json.dumps(pairs_batch, ensure_ascii=False, indent=2)
    
    prompt = f"""
    あなたはプロのゲーム翻訳者です。以下のJSONデータは、ゲームのスキルや能力に関する日英のテキストペアのリストです。
    これらを分析し、全てのテキストから重要な用語ペアを抽出して、単一のJSONリストにまとめてください。

    抽出対象:
    - 固有名詞 (キャラクター名、地名など)
    - スキル名 (Basic Attack, EX Special Attackなど)
    - ステータス・属性名 (Ice Attribute, Dazeなど)
    - ゲーム内キーワード
    
    ルール:
    1. 英語側で <strong> タグなどで強調されている単語は特に重要です。
    2. 日本語側はカギ括弧『』や「」で囲まれていることが多いですが、囲まれていない場合もあります。
    3. 文脈から判断して、意味が対応する最小単位の語句を抜き出してください。
    4. 一般的な動詞や接続詞は除外してください。
    5. 結果は必ず JSON形式のリスト [{{ "en": "...", "ja": "..." }}, ...] のみを出力してください。
    6. Markdownのコードブロックは使用しないでください。

    Input Data (JSON):
    {input_json}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        print(f"  AI Error: {e}")
        return []

def scrape_official_wiki(target_id=None):
    all_pairs = []
    
    # APIキーチェック
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("エラー: GOOGLE_API_KEY が設定されていません。")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        if target_id:
            entry_ids = [str(target_id)]
            print(f"Targeting specific character ID: {target_id}")
        else:
            entry_ids = get_character_entry_ids(browser)
            print(f"Total characters found: {len(entry_ids)}")
        
        # 各キャラクターの詳細ページを処理
        for index, entry_id in enumerate(entry_ids):
            print(f"Processing Character [{index+1}/{len(entry_ids)}] ID: {entry_id}")
            
            url_en = f"https://wiki.hoyolab.com/pc/zzz/entry/{entry_id}?lang=en-us"
            url_jp = f"https://wiki.hoyolab.com/pc/zzz/entry/{entry_id}?lang=ja-jp"
            
            # --- 日本語版 ---
            print("  [JP] Loading page...") # ログ追加
            page_jp = browser.new_page()
            try:
                page_jp.goto(url_jp, wait_until="networkidle", timeout=30000)
                page_jp.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                # 存在チェック (404などの場合)
                if page_jp.locator("text=Page Not Found").count() > 0:
                    print("  JP Page not found, skipping.")
                    page_jp.close()
                    continue

                mindscape_jp = extract_mindscape_from_html(page_jp.content())
                skills_jp = extract_skills_interactively(page_jp)
                data_jp = mindscape_jp + skills_jp
            except Exception as e:
                print(f"  Error loading JP page: {e}")
                page_jp.close()
                continue
            page_jp.close()

            # --- 英語版 ---
            print("  [EN] Loading page...") # ログ追加
            page_en = browser.new_page()
            try:
                page_en.goto(url_en, wait_until="networkidle", timeout=30000)
                page_en.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                if page_en.locator("text=Page Not Found").count() > 0:
                    print("  EN Page not found, skipping.")
                    page_en.close()
                    continue

                mindscape_en = extract_mindscape_from_html(page_en.content())
                skills_en = extract_skills_interactively(page_en)
                data_en = mindscape_en + skills_en
            except Exception as e:
                print(f"  Error loading EN page: {e}")
                page_en.close()
                continue
            page_en.close()

            # --- 突き合わせ ---
            # Mindscape
            m_jp = [d for d in data_jp if d["type"] == "MindscapeDesc"]
            m_en = [d for d in data_en if d["type"] == "MindscapeDesc"]
            count_m = min(len(m_jp), len(m_en))
            
            mindscape_names = []
            for i in range(count_m):
                all_pairs.append([m_en[i]["title"], m_en[i]["value"], m_jp[i]["title"], m_jp[i]["value"]])
                mindscape_names.append(m_jp[i]["title"])

            # Skills (インデックスベースのマッチング)
            # 英語版で欠損があっても、(skill_idx, tab_idx) が一致するものだけをペアにする
            s_jp_map = {(d["skill_idx"], d["tab_idx"]): d for d in data_jp if d["type"] == "SkillDesc"}
            s_en_map = {(d["skill_idx"], d["tab_idx"]): d for d in data_en if d["type"] == "SkillDesc"}
            
            skill_names = []
            
            # 日本語データを基準にループ
            for key, item_jp in s_jp_map.items():
                if key in s_en_map:
                    item_en = s_en_map[key]
                    all_pairs.append([item_en["title"], item_en["value"], item_jp["title"], item_jp["value"]])
                    skill_names.append(f"{item_jp['title']}(S{key[0]+1}-T{key[1]+1})")
                else:
                    # 英語版に存在しない場合はスキップし、警告を出す
                    print(f"  Warning: No matching EN skill found for JP: {item_jp['title']} (S{key[0]+1}-T{key[1]+1})")

            print(f"  Collected {count_m} mindscapes: {', '.join(mindscape_names)}")
            print(f"  Collected {len(skill_names)} skills: {', '.join(skill_names)}")
            
            # 中間保存 (万が一途中で止まった時のため)
            if (index + 1) % 5 == 0:
                print("  Saving intermediate results...")
                with open("resource/zzz_pairs_temp.csv", "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(all_pairs)

        browser.close()

    if not all_pairs:
        print("データが見つかりませんでした。")
        return

    # --- 3. AIによる用語抽出処理 (バッチ処理) ---
    BATCH_SIZE = 12  # 一度に処理するペア数
    
    # 処理対象のデータを整形
    process_items = []
    final_glossary = []

    for pair in all_pairs:
        en_title, en_desc, ja_title, ja_desc = pair
        
        # タイトル自体も用語として追加
        final_glossary.append({"en": en_title, "ja": ja_title})
        
        if len(en_desc) < 5 or len(ja_desc) < 5:
            continue
            
        process_items.append({
            "en_title": en_title,
            "en_desc": en_desc,
            "ja_title": ja_title,
            "ja_desc": ja_desc
        })

    print(f"Gemini APIを使用して {len(process_items)} 件のテキストペアから用語を抽出します (Batch Size: {BATCH_SIZE})...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # バッチループ
    for i in tqdm(range(0, len(process_items), BATCH_SIZE)):
        batch = process_items[i : i + BATCH_SIZE]
        terms = extract_terms_batch_with_ai(model, batch)
        if terms:
            final_glossary.extend(terms)
        
        # レート制限回避のための待機
        time.sleep(2.0)

    # --- 4. CSV保存 ---
    if final_glossary:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        unique_glossary = []
        seen = set()
        for item in final_glossary:
            en_term = item.get("en", "").strip()
            ja_term = item.get("ja", "").strip()
            
            if not en_term or not ja_term: continue
            if len(en_term) == 1 and not en_term.isalnum(): continue

            pair = (en_term, ja_term)
            if pair not in seen:
                unique_glossary.append(pair)
                seen.add(pair)

        with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["en", "ja"])
            writer.writerows(unique_glossary)
        
        print(f"保存完了: {OUTPUT_FILE} ({len(unique_glossary)}ペア)")
    else:
        print("用語が見つかりませんでした。")

if __name__ == "__main__":
    # コマンドライン引数でID
    if len(sys.argv) > 1:
        try:
            target_id = int(sys.argv[1])
            scrape_official_wiki(target_id)
        except ValueError:
            print("無効なIDが指定されました。")
    else:
        scrape_official_wiki()