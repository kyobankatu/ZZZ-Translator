import xml.etree.ElementTree as ET
import csv
import re
import sys
import os

# --- 設定 ---
# XMLファイルのパス (デスクトップにあるファイルを指定)
XML_FILE = "/Users/kota/Desktop/zenlesszonezero_pages_current.xml"
# 出力するCSVファイル名
OUTPUT_CSV = "zzz_glossary.csv"
# ------------

def get_template_content(text, template_name):
    """
    テキストから指定されたテンプレートの中身を抽出する。
    ネストされた {{ }} に対応するため、単純な正規表現ではなく括弧のバランスをカウントします。
    """
    # テンプレートの開始位置を探す (大文字小文字区別なし)
    # {{TemplateName|... または {{TemplateName}} にマッチ
    pattern = re.compile(r'\{\{\s*' + re.escape(template_name) + r'\s*[|}]', re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return None
    
    start_pos = match.start()
    balance = 0
    i = start_pos
    length = len(text)
    
    while i < length:
        if text[i:i+2] == '{{':
            balance += 1
            i += 2
            continue
        elif text[i:i+2] == '}}':
            balance -= 1
            i += 2
            if balance == 0:
                # テンプレート全体を返す ({{ ... }})
                return text[start_pos:i]
            continue
        i += 1
    return None

def parse_template_params(template_text):
    """
    テンプレート文字列からパラメータを辞書形式で抽出する
    例: {{Other Languages|en=Name|ja=名前}} -> {'en': 'Name', 'ja': '名前'}
    """
    # 外側の {{ }} を除去
    content = template_text[2:-2]
    
    params = {}
    # パイプ | で分割するが、ネストされたリンク [[A|B]] 内のパイプは無視したい
    # 簡易的に、行頭または | の直後にパラメータ名が来る構造を利用して抽出
    
    # 単純な split('|') だとリンク内のパイプで壊れるため、正規表現で key=value を探す
    # 行頭またはパイプの後に、空白、キー、=、値、というパターン
    # 値は次のパイプまたは末尾まで (非貪欲)
    
    # 簡易パーサー: パイプで分割し、'='が含まれるものを採用する
    # (厳密なMediaWikiパースは複雑なため、用語集用途として割り切る)
    parts = content.split('|')
    
    for part in parts:
        if '=' in part:
            # 最初の = で分割
            key, val = part.split('=', 1)
            params[key.strip()] = val.strip()
            
    return params

def clean_wikitext(text):
    """Wiki記法を除去してプレーンテキストにする"""
    if not text:
        return ""
    
    # [[Link|Text]] -> Text
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)
    # HTMLタグ除去 (<br>, <small>など)
    text = re.sub(r'<[^>]+>', '', text)
    # 連続する空白を1つに
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    if not os.path.exists(XML_FILE):
        print(f"エラー: XMLファイルが見つかりません: {XML_FILE}")
        print("正しいパスを設定してください。")
        return

    print(f"XMLファイルを解析中: {XML_FILE} ...")
    
    try:
        # XMLをパース
        # iterparseを使うとメモリ効率が良いが、ファイルサイズが数GBでなければparseで十分
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
    except Exception as e:
        print(f"XML解析エラー: {e}")
        return

    # MediaWikiのエクスポートXMLには名前空間がついている場合がある
    # 例: {http://www.mediawiki.org/xml/export-0.11/}
    m = re.match(r'\{(.*)\}', root.tag)
    ns = {'mw': m.group(1)} if m else {}
    
    # ページ要素を取得
    pages = root.findall('mw:page', ns) if ns else root.findall('page')
    print(f"ページ数: {len(pages)}")

    results = []
    
    for page in pages:
        # タイトル取得
        title_elem = page.find('mw:title', ns) if ns else page.find('title')
        if title_elem is None: continue
        title = title_elem.text

        # 名前空間チェック (標準名前空間 '0' のみ対象)
        ns_elem = page.find('mw:ns', ns) if ns else page.find('ns')
        if ns_elem is not None and ns_elem.text != '0':
            continue

        # 本文取得
        revision = page.find('mw:revision', ns) if ns else page.find('revision')
        if revision is None: continue
        text_elem = revision.find('mw:text', ns) if ns else revision.find('text')
        if text_elem is None or text_elem.text is None: continue
        
        text = text_elem.text

        # {{Other Languages}} テンプレートを探す
        ol_template = get_template_content(text, "Other Languages")
        
        if ol_template:
            params = parse_template_params(ol_template)
            
            ja_text = params.get('ja')
            en_text = params.get('en')
            
            # enパラメータがない場合はページタイトルを使用
            if not en_text:
                en_text = title
            
            if ja_text and en_text:
                clean_ja = clean_wikitext(ja_text)
                clean_en = clean_wikitext(en_text)
                
                # 日本語があり、かつ英語と異なる場合のみ登録
                if clean_ja and clean_ja != clean_en:
                    results.append({'en': clean_en, 'ja': clean_ja})

    # CSV書き出し
    if results:
        print(f"抽出された用語数: {len(results)}")
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['en', 'ja'])
            writer.writeheader()
            writer.writerows(results)
        print(f"保存完了: {OUTPUT_CSV}")
    else:
        print("用語が見つかりませんでした。")

if __name__ == "__main__":
    main()