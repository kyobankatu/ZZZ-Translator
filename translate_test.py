import pandas as pd
import html
import yaml
from google.cloud import translate_v3 as translate

def run_glossary_test(
    project_id="YOUR_PROJECT_ID",
    glossary_id="YOUR_GLOSSARY_ID",
    location="LOCATION"
):
    client = translate.TranslationServiceClient()
    parent = f"projects/{project_id}/locations/{location}"
    
    glossary_path = client.glossary_path(project_id, location, glossary_id)
    glossary_config = translate.types.TranslateTextGlossaryConfig(
        glossary=glossary_path
    )

    try:
        df = pd.read_csv("zzz_glossary.csv")
        sample_size = min(10, len(df))
        samples = df.sample(n=sample_size)
    except Exception as e:
        print(f"エラー: CSVファイルの読み込みに失敗しました。\n{e}")
        return

    print(f"--- 用語集テスト開始 ({sample_size}件) ---\n")
    success_count = 0

    for index, row in samples.iterrows():
        source_text = row['en']
        expected_text = row['ja']

        response = client.translate_text(
            request={
                "contents": [source_text],
                "target_language_code": "ja",
                "source_language_code": "en",
                "parent": parent,
                "glossary_config": glossary_config,
                "mime_type": "text/plain", # 明示的に指定することをおすすめします
            }
        )

        if response.glossary_translations:
            raw_text = response.glossary_translations[0].translated_text
        else:
            raw_text = response.translations[0].translated_text

        # --- 追加 2: ここで &quot; を " に戻します ---
        actual_text = html.unescape(raw_text)
        # ----------------------------------------

        # 比較（前後の空白除去も忘れずに）
        is_match = (actual_text.strip() == expected_text.strip())
        
        result_mark = "✅ OK" if is_match else "❌ NG"
        if is_match:
            success_count += 1

        print(f"原文 (en)  : {source_text}")
        print(f"期待値 (ja): {expected_text}")
        print(f"翻訳結果   : {actual_text}") # 修正後のテキストを表示
        print(f"判定       : {result_mark}")
        print("-" * 30)

    print(f"\nテスト完了: {success_count}/{sample_size} 件 合格")

if __name__ == "__main__":
    # data.yml から設定を読み込む
    with open("data.yml", "r") as f:
        config = yaml.safe_load(f)

    run_glossary_test(
        project_id=config["project_id"],
        glossary_id=config["glossary_id"],
        location=config["location"]
    )