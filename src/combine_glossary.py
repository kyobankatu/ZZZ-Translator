import pandas as pd
import yaml
import os
import re
import inflect
import time
import csv
import google.generativeai as genai
from tqdm import tqdm

# キャッシュファイルのパス
CACHE_FILE = "resource/ai_cleaning_cache.csv"

def load_cache():
    """キャッシュファイルを読み込み、辞書として返す"""
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, mode='r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        cache[row[0]] = row[1]
            print(f"キャッシュを読み込みました: {len(cache)}件")
        except Exception as e:
            print(f"キャッシュ読み込みエラー: {e}")
    return cache

def save_to_cache(new_data):
    """新しいクリーニング結果をキャッシュに追記する"""
    if not new_data:
        return
    try:
        # 追記モードで開く
        with open(CACHE_FILE, mode='a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for original, cleaned in new_data.items():
                writer.writerow([original, cleaned])
        print(f"キャッシュに {len(new_data)} 件追記しました。")
    except Exception as e:
        print(f"キャッシュ保存エラー: {e}")

def clean_text_with_ai(model, text_list):
    """
    Gemini APIを使ってリスト内のテキストを一括クリーニングする
    """
    prompt = """
    以下のリストは「ゲーム用語の日本語訳」ですが、末尾に不要なローマ字読みや注釈、英語の重複が含まれているものがあります。
    これらを削除し、正しい日本語の名称のみに修正してください。
    
    ルール:
    1. ローマ字読みや発音記号（Zenresu...）は削除する。
    2. 英語の重複（Chapter 1...）は削除する。
    3. 記号だけの注釈（[!][!]）は削除する。
    4. 正しい日本語タイトル（「マークII」「BGM、ON」など）は維持する。
    5. 出力は修正後のテキストのみを、入力と同じ順序で改行区切りで出力すること。
    6. 余計な説明は一切不要。

    入力リスト:
    """
    
    input_text = "\n".join(text_list)
    
    try:
        response = model.generate_content(prompt + input_text)
        cleaned_text = response.text.strip().split('\n')
        
        # 入力と出力の数が合わない場合の安全策
        if len(cleaned_text) != len(text_list):
            return text_list 
            
        return [t.strip() for t in cleaned_text]
    except Exception as e:
        print(f"API Error: {e}")
        return text_list

def combine_glossaries():
    # data.yml から設定を読み込む
    config_path = "resource/data.yml"
    if not os.path.exists(config_path):
        print(f"エラー: {config_path} が見つかりません。")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 結合対象のファイルリストを作成
    target_files = []
    if "scraping_output" in config: target_files.append(config["scraping_output"])
    if "xml_output" in config: target_files.append(config["xml_output"])
    if "detail_output" in config: target_files.append(config["detail_output"])
    if "additional_glossary" in config: target_files.append(config["additional_glossary"])

    output_file = "resource/zzz_glossary.csv"
    combined_data = []

    print("--- 用語集の結合処理を開始 ---")

    for file_path in target_files:
        if not os.path.exists(file_path):
            print(f"スキップ (ファイルなし): {file_path}")
            continue
        try:
            df = pd.read_csv(file_path)
            combined_data.append(df)
            print(f"読み込み: {file_path} ({len(df)}件)")
        except Exception as e:
            print(f"エラー: {file_path} の読み込みに失敗しました。\n{e}")

    if combined_data:
        # データを結合
        combined_df = pd.concat(combined_data, ignore_index=True)
        
        # --- AIによるクリーニング処理 (日本語と英語が混在するもののみ) ---
        api_key = os.environ.get("GOOGLE_API_KEY")
        
        if not api_key:
            print("警告: GOOGLE_API_KEY が設定されていません。AIクリーニングをスキップします。")
        else:
            # キャッシュの読み込み
            cache = load_cache()
            
            def is_mixed_jp_en(text):
                if not isinstance(text, str): return False
                has_jp = re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text)
                has_en = re.search(r'[a-zA-Z]', text)
                return bool(has_jp and has_en)

            # 処理対象の抽出
            target_mask = combined_df['ja'].apply(is_mixed_jp_en)
            target_indices = combined_df[target_mask].index.tolist()
            
            if target_indices:
                print(f"対象候補: {len(target_indices)}件 (日本語・英語混在)")
                
                indices_to_process = []
                updates_from_cache = {}

                # キャッシュにあるものは即適用、ないものはAPI処理リストへ
                for idx in target_indices:
                    original_text = combined_df.at[idx, 'ja']
                    if original_text in cache:
                        updates_from_cache[idx] = cache[original_text]
                    else:
                        indices_to_process.append(idx)
                
                # キャッシュ適用
                if updates_from_cache:
                    print(f"キャッシュから {len(updates_from_cache)} 件を適用します。")
                    for idx, cleaned in updates_from_cache.items():
                        combined_df.at[idx, 'ja'] = cleaned

                # API処理が必要なものがある場合
                if indices_to_process:
                    print(f"新たにAIクリーニングを実行します: {len(indices_to_process)}件")
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    batch_size = 50
                    new_cache_data = {}
                    
                    for i in tqdm(range(0, len(indices_to_process), batch_size)):
                        batch_indices = indices_to_process[i:i+batch_size]
                        batch_texts = combined_df.loc[batch_indices, 'ja'].tolist()
                        
                        cleaned_texts = clean_text_with_ai(model, batch_texts)
                        
                        for idx, original, cleaned in zip(batch_indices, batch_texts, cleaned_texts):
                            combined_df.at[idx, 'ja'] = cleaned
                            new_cache_data[original] = cleaned
                        
                        time.sleep(10) # レート制限回避

                    # 新しい結果をキャッシュに保存
                    save_to_cache(new_cache_data)
                else:
                    print("全ての対象データがキャッシュ済みのため、APIリクエストはスキップされました。")

            else:
                print("クリーニング対象が見つかりませんでした。")
        # -------------------------------------------------------

        # inflectエンジンの初期化
        p = inflect.engine()

        # --- 追加処理: バリエーションの生成 ---
        new_rows = []
        for index, row in combined_df.iterrows():
            en_term = str(row['en']).strip() # 空白除去を追加
            ja_term = str(row['ja']).strip()

            # 1. 複数形の追加 (英語のみ)
            # 空文字でない、かつ単語数が4以下の場合のみ処理
            if en_term and len(en_term.split()) <= 4:
                try:
                    plural_en = p.plural(en_term)
                    if plural_en and plural_en != en_term:
                        new_rows.append({'en': plural_en, 'ja': ja_term})
                except Exception:
                    # inflectでエラーが出ても無視して次へ進む
                    pass

            # 2. タグ・カテゴリ除去バージョンの追加
            # [Tag] 形式の除去
            cleaned_en = re.sub(r'^\[.*?\]\s*', '', en_term)
            cleaned_ja = re.sub(r'^\[.*?\]\s*', '', ja_term)

            # Category: 形式の除去 (コロン区切りの接頭辞を除去)
            # 例: "Defensive Assist: Drifting Petalss" -> "Drifting Petalss"
            # 例: "パリィ支援：花筏" -> "花筏"
            cleaned_en = re.sub(r'^.+?[:：]\s*', '', cleaned_en)
            cleaned_ja = re.sub(r'^.+?[:：]\s*', '', cleaned_ja)

            if (cleaned_en != en_term or cleaned_ja != ja_term):
                if len(cleaned_en) > 1 and len(cleaned_ja) > 0:
                    new_rows.append({'en': cleaned_en, 'ja': cleaned_ja})

        if new_rows:
            variations_df = pd.DataFrame(new_rows)
            combined_df = pd.concat([combined_df, variations_df], ignore_index=True)
            print(f"バリエーション追加: {len(new_rows)}件")
        # ------------------------------------

        # 重複を削除
        before_count = len(combined_df)
        combined_df.drop_duplicates(subset=['en', 'ja'], inplace=True)
        after_count = len(combined_df)
        
        print(f"重複削除: {before_count} -> {after_count} ({before_count - after_count}件削除)")

        # 結合したデータを保存
        combined_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"結合した用語集を {output_file} に保存しました。")
    else:
        print("結合するデータがありませんでした。")

if __name__ == "__main__":
    combine_glossaries()