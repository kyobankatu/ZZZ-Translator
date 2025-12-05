import xml.etree.ElementTree as ET
import csv
import re
import os
import yaml

def get_template_content(text, template_name):
    """
    テキストから指定されたテンプレートの中身を抽出する。
    ネストされた {{ }} に対応するため、単純な正規表現ではなく括弧のバランスをカウントします。
    """
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
                return text[start_pos:i]
            continue
        i += 1
    return None

def parse_template_params(template_text):
    """
    テンプレート文字列からパラメータを辞書形式で抽出する
    例: {{Other Languages|en=Name|ja=名前}} -> {'en': 'Name', 'ja': '名前'}
    """
    content = template_text[2:-2]
    
    params = {}
    parts = content.split('|')
    
    for part in parts:
        if '=' in part:
            key, val = part.split('=', 1)
            params[key.strip()] = val.strip()
            
    return params

def clean_wikitext(text):
    """Wiki記法を除去してプレーンテキストにする"""
    if not text:
        return ""
    
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    config = {}
    if os.path.exists("resource/data.yml"):
        with open("resource/data.yml", "r") as f:
            config = yaml.safe_load(f)
    
    xml_file = config.get("xml_file")
    output_csv = config.get("xml_output")
    if not xml_file:
        print("エラー: data.yml に xml_file の設定がありません。")
        return
    if not output_csv:
        print("エラー: data.yml に xml_output の設定がありません。")
        return

    if not os.path.exists(xml_file):
        print(f"エラー: XMLファイルが見つかりません: {xml_file}")
        print("data.yml の xml_file の設定を確認してください。")
        return

    print(f"XMLファイルを解析中: {xml_file} ...")
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"XML解析エラー: {e}")
        return

    m = re.match(r'\{(.*)\}', root.tag)
    ns = {'mw': m.group(1)} if m else {}
    
    pages = root.findall('mw:page', ns) if ns else root.findall('page')
    print(f"ページ数: {len(pages)}")

    results = []
    
    for page in pages:
        title_elem = page.find('mw:title', ns) if ns else page.find('title')
        if title_elem is None: continue
        title = title_elem.text

        ns_elem = page.find('mw:ns', ns) if ns else page.find('ns')
        if ns_elem is not None and ns_elem.text != '0':
            continue

        revision = page.find('mw:revision', ns) if ns else page.find('revision')
        if revision is None: continue
        text_elem = revision.find('mw:text', ns) if ns else revision.find('text')
        if text_elem is None or text_elem.text is None: continue
        
        text = text_elem.text

        ol_template = get_template_content(text, "Other Languages")
        
        if ol_template:
            params = parse_template_params(ol_template)
            
            ja_text = params.get('ja')
            en_text = params.get('en')
            
            if not en_text:
                en_text = title
            
            if ja_text and en_text:
                clean_ja = clean_wikitext(ja_text)
                clean_en = clean_wikitext(en_text)
                
                if clean_ja and clean_ja != clean_en:
                    results.append({'en': clean_en, 'ja': clean_ja})

    if results:
        print(f"抽出された用語数: {len(results)}")
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['en', 'ja'])
            writer.writeheader()
            writer.writerows(results)
        print(f"保存完了: {output_csv}")
    else:
        print("用語が見つかりませんでした。")

if __name__ == "__main__":
    main()