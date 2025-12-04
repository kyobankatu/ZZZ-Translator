import os
import time
import json
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ベースURL
BASE_URL = "https://zenless-zone-zero.fandom.com"

# WebからAllPagesのURLリストを取得する
def get_page_urls_from_web():
  url = "https://zenless-zone-zero.fandom.com/wiki/Special:AllPages"
  urls = []
  
  try:
    print(f"Fetching AllPages list from: {url}")
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # <ul class="mw-allpages-chunk"> の中の li > a を探す
    chunk_ul = soup.find('ul', class_='mw-allpages-chunk')
    if chunk_ul:
      links = chunk_ul.find_all('a')
      for link in links:
        href = link.get('href')
        if href:
          full_url = urljoin(BASE_URL, href)
          urls.append(full_url)
  except Exception as e:
    print(f"Error fetching AllPages: {e}")

  return urls

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
      header = soup.find('h1', class_='page-header__title')
      if header:
        page_title = header.get_text(strip=True)
        english_name = page_title
        japanese_name = page_title

    return english_name, japanese_name

  except Exception as e:
    print(f"Error fetching {url}: {e}")
    return None, None

def main():
  # WebからURLリストを取得
  urls = get_page_urls_from_web()
  print(f"Found {len(urls)} pages.")

  dataset = []

  for url in urls:
    en, ja = extract_names_from_url(url)
    
    if en and ja:
      print(f"  Found: EN={en}, JA={ja}")
      dataset.append({
        "english": en,
        "japanese": ja
      })
    else:
      print("  Skipping: Translation not found.")
    
    # サーバー負荷軽減のため待機
    #time.sleep(1)

  # CSVファイルとして保存 (Google Cloud Translation API Glossary format)
  output_file = "zzz_glossary.csv"
  with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    # ヘッダー書き込み
    writer.writerow(['en', 'ja'])
    
    # データ書き込み
    for item in dataset:
      writer.writerow([item['english'], item['japanese']])
  
  print(f"Saved {len(dataset)} items to {output_file}")

if __name__== "__main__":
  main()