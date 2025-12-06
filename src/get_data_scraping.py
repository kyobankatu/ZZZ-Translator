import time
import csv
import requests
import yaml
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ベースURL
BASE_URL = "https://zenless-zone-zero.fandom.com"

# WebからAllPagesのURLリストを取得する (全ページ対応版)
def get_page_urls_from_web():
    # 最初のページ
    current_url = "https://zenless-zone-zero.fandom.com/wiki/Special:AllPages"
    all_urls = []
    
    while current_url:
        try:
            print(f"Fetching AllPages list from: {current_url}")
            response = requests.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 現在のページのリストから記事URLを抽出
            chunk_ul = soup.find('ul', class_='mw-allpages-chunk')
            if chunk_ul:
                links = chunk_ul.find_all('a')
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(BASE_URL, href)
                        all_urls.append(full_url)
            
            # 2. "Next page" のリンクを探して次へ遷移する
            next_link = soup.find('a', string=lambda text: text and "Next page" in text)

            if next_link:
                next_href = next_link.get('href')
                current_url = urljoin(BASE_URL, next_href)
            else:
                print("No 'Next page' link found. Reached the last page.")
                current_url = None

        except Exception as e:
            print(f"Error fetching AllPages: {e}")
            break

    return all_urls

# 個別のページから日英の名称を抽出する
def extract_names_from_url(url):
    try:
        print(f"Fetching: {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        english_name = None
        japanese_name = None

        # <table class="article-table alternating-colors-table"> を探す
        tables = soup.find_all('table', class_='article-table alternating-colors-table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 2:
                    lang = cols[0].get_text(strip=True)
                    name = cols[1].get_text(strip=True)
                    
                    if lang == "English":
                        english_name = name
                    elif lang == "Japanese":
                        japanese_name = name
            
            # 両方見つかったらループを抜ける
            if english_name and japanese_name:
                break
        
        # テーブルでEnglishが見つかり、Japaneseが見つからない場合 -> 日本語に英語名を適用
        if english_name and not japanese_name:
            japanese_name = english_name

        # Englishが見つからない場合（テーブルがない、またはテーブルに情報がない） -> ページタイトルを両方に適用
        if not english_name:
            english_name = None
            japanese_name = None

        return english_name, japanese_name

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, None

def main():
    # data.yml から設定を読み込む
    config = {}
    if os.path.exists("resource/data.yml"):
        with open("resource/data.yml", "r") as f:
            config = yaml.safe_load(f)
    
    output_file = config.get("scraping_output")
    if not output_file:
        print("エラー: data.yml に scraping_output の設定がありません。")
        return

    # WebからURLリストを取得
    urls = get_page_urls_from_web()
    print(f"Found {len(urls)} pages.")

    # 出力パスの調整: 設定値にディレクトリが含まれていない場合は resource/ を付与
    if os.path.dirname(output_file):
        save_path = output_file
    else:
        save_path = os.path.join("resource", output_file)

    print(f"Output file: {save_path}")

    # CSVファイルを書き込みモードで開き、ヘッダーを書き込む
    with open(save_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['en', 'ja'])
        
        buffer = []
        total_saved = 0
        BATCH_SIZE = 30

        for url in urls:
            en, ja = extract_names_from_url(url)
            
            if en and ja:
                print(f"  Found: EN={en}, JA={ja}")
                buffer.append([en, ja])
            else:
                print("  Skipping: Translation not found.")
            
            # バッファが溜まったら書き込む
            if len(buffer) >= BATCH_SIZE:
                writer.writerows(buffer)
                total_saved += len(buffer)
                print(f"  -> Saved batch of {len(buffer)} items (Total: {total_saved})")
                buffer = [] # バッファをクリア
                f.flush()   # ディスクへの書き込みを確実にする

            # サーバー負荷軽減のため待機
            #time.sleep(0.5)

        # ループ終了後、残りのデータを書き込む
        if buffer:
            writer.writerows(buffer)
            total_saved += len(buffer)
            print(f"  -> Saved remaining {len(buffer)} items")
    
    print(f"Saved total {total_saved} items to {save_path}")

if __name__== "__main__":
    main()