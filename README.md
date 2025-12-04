# ZZZ-Translator

Zenless Zone Zero (ゼンレスゾーンゼロ) のWikiから用語データを取得し、Google Cloud Translation API の用語集 (Glossary) を構築・検証するためのツールセット。

## 主要機能

*   **用語データ収集**: Fandom Wikiからキャラクター名や専門用語の日英対訳を自動抽出し、CSV形式で保存
*   **用語集管理**: Google Cloud Translation API への用語集リソースの登録および更新（再作成）
*   **翻訳検証**: 登録された用語集を使用し、実際の翻訳結果と期待値（Wikiの対訳）を比較検証

## 使用方法

1.  **設定ファイルの準備**:
    `data.yml` を編集し、GCPプロジェクトID、リージョン、GCSバケットURIなどを設定する。
2.  **データ取得**:
    ```bash
    python get_data.py
    ```
    実行後、ローカルに `zzz_glossary.csv` が生成される。
3.  **CSVのアップロード**:
    生成された `zzz_glossary.csv` を、`data.yml` の `bucket_uri` で指定したGoogle Cloud Storageのパスへ手動でアップロードする。
    ```bash
    # 例: gsutilを使用する場合
    gsutil cp zzz_glossary.csv gs://YOUR_BUCKET_NAME/zzz_glossary.csv
    ```
4.  **用語集の登録**:
    ```bash
    python add_glossary.py
    ```
    GCS上のCSVファイルを参照し、Translation APIに用語集リソースを作成する（既存の同名用語集は削除される）。
5.  **翻訳テスト**:
    ```bash
    python translate_test.py
    ```
    用語集を使用した翻訳を実行し、結果をコンソールに出力する。

## 動作環境

*   **OS**: macOS, Linux, Windows
*   **言語**: Python 3.x
*   **クラウド基盤**: Google Cloud Platform (GCP)
    *   Cloud Translation API (Advanced)
    *   Cloud Storage

## インストール・実行方法

### 1. 事前準備
*   GCPプロジェクトの作成と課金有効化
*   Translation API (Advanced) の有効化
*   Cloud Storage バケットの作成
*   `gcloud` CLI のインストールと認証
    ```bash
    gcloud auth application-default login
    ```

### 2. 依存ライブラリのインストール
```bash
pip install requests beautifulsoup4 google-cloud-translate google-cloud-storage pandas PyYAML