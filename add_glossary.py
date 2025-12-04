import yaml
from google.cloud import translate_v3 as translate
from google.api_core.exceptions import NotFound

def recreate_glossary(
    project_id="YOUR_PROJECT_ID",
    bucket_uri="YOUR_GCS_BUCKET_URI",
    glossary_id="YOUR_GLOSSARY_ID",
    location="LOCATION"
):
    client = translate.TranslationServiceClient()
    parent = f"projects/{project_id}/locations/{location}"
    name = f"{parent}/glossaries/{glossary_id}"

    print(f"--- 用語集の再構築を開始します ---")
    print(f"Target: {name}")

    # 1. 既存の用語集があれば削除
    try:
        print("1. 既存の用語集を検索中...")
        client.get_glossary(name=name)
        print("   -> 見つかりました。削除を実行します...")
        operation = client.delete_glossary(name=name)
        operation.result(timeout=180)
        print("   -> 削除完了。")
    except NotFound:
        print("   -> 既存の用語集はありませんでした。")

    # 2. 新規作成
    print("2. 新しい用語集を作成中 (GCSから読み込み)...")
    
    language_codes_set = translate.types.Glossary.LanguageCodesSet(
        language_codes=["en", "ja"]
    )

    glossary_config = translate.types.Glossary(
        name=name,
        language_codes_set=language_codes_set,
        input_config=translate.types.GlossaryInputConfig(
            gcs_source=translate.types.GcsSource(input_uri=bucket_uri)
        ),
    )

    operation = client.create_glossary(parent=parent, glossary=glossary_config)
    result = operation.result(timeout=180)

    # 3. 結果確認
    print("3. 作成完了！ステータス確認:")
    print(f"   - 名前: {result.name}")
    print(f"   - エントリ数: {result.entry_count} 件") # ★ここが 0 だと失敗しています
    print(f"   - 入力URI: {result.input_config.gcs_source.input_uri}")

    if result.entry_count > 0:
        print("\n✅ 成功です！これでテストプログラムを再実行してください。")
    else:
        print("\n⚠️ 警告: エントリ数が 0 です。CSVファイルの中身やGCSパスを確認してください。")

if __name__ == "__main__":
    # data.yml から設定を読み込む
    with open("data.yml", "r") as f:
        config = yaml.safe_load(f)

    recreate_glossary(
        project_id=config["project_id"],
        bucket_uri=config["bucket_uri"],
        glossary_id=config["glossary_id"],
        location=config["location"]
    )