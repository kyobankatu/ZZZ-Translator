import yaml
import re
import sys
from google.cloud import translate_v3 as translate
from google.cloud import storage
from google.api_core.exceptions import NotFound

def upload_to_gcs(project_id, local_file, bucket_uri):
    """ローカルファイルをGCSにアップロードする"""
    # gs://bucket_name/path/to/file からバケット名とパスを抽出
    match = re.match(r'gs://([^/]+)/(.+)', bucket_uri)
    if not match:
        print(f"エラー: bucket_uri の形式が不正です: {bucket_uri}")
        return False

    bucket_name = match.group(1)
    blob_name = match.group(2)

    print(f"0. GCSへアップロード中: {local_file} -> {bucket_uri}")
    try:
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_file)
        print("   -> アップロード完了。")
        return True
    except Exception as e:
        print(f"   -> アップロード失敗: {e}")
        return False

def recreate_glossary(
    project_id="YOUR_PROJECT_ID",
    bucket_uri="YOUR_GCS_BUCKET_URI",
    glossary_id="YOUR_GLOSSARY_ID",
    location="LOCATION"
):
    local_csv_file = "zzz_glossary.csv"  # ローカルのCSVファイル名
    # --- 追加: CSVのアップロード処理 ---
    if local_csv_file:
        if not upload_to_gcs(project_id, local_csv_file, bucket_uri):
            print("処理を中断します。")
            return
    # --------------------------------

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
    print(f"   - エントリ数: {result.entry_count} 件")
    print(f"   - 入力URI: {result.input_config.gcs_source.input_uri}")

    if result.entry_count > 0:
        print("\n✅ 成功です！これでテストプログラムを再実行してください。")
    else:
        print("\n⚠️ 警告: エントリ数が 0 です。CSVファイルの中身やGCSパスを確認してください。")

if __name__ == "__main__":
    # data.yml から設定を読み込む
    with open("data.yml", "r") as f:
        config = yaml.safe_load(f)

    # csv_file キーがない場合のフォールバック
    csv_file = config.get("csv_file", "zzz_glossary.csv")

    recreate_glossary(
        project_id=config["project_id"],
        bucket_uri=config["bucket_uri"],
        glossary_id=config["glossary_id"],
        location=config["location"]
    )