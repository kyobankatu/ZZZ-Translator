# ZZZ-Translator

Zenless Zone Zero (ゼンレスゾーンゼロ) のWikiデータから用語を抽出し、Google Cloud Translation API の用語集 (Glossary) を構築・検証するためのツールセット。

## 主要機能

*   **用語データ抽出**:
    *   **XML解析 (推奨)**: Wikiのダンプデータ (XML) から高速に用語ペアを抽出。
    *   **Webスクレイピング**: Fandom Wikiから直接データを収集。
*   **用語集管理**: CSVファイルのGCSへの自動アップロードと、Translation API への用語集リソース登録・更新。
*   **翻訳検証**: 登録された用語集を使用し、実際の翻訳結果と期待値（Wikiの対訳）を比較検証。

## 使用方法

1.  **設定ファイルの準備**:
    `data.yml` を編集し、GCPプロジェクトID、リージョン、GCSバケットURIなどを設定する。

2.  **データ取得**:
    以下のいずれかの方法で `zzz_glossary.csv` を生成する。

    *   **方法A: XMLダンプから抽出 (推奨)**
        WikiのXMLダンプファイルを用意し、`get_data_xml.py` 内のパスを指定して実行。
        ```bash
        python get_data_xml.py
        ```
    *   **方法B: Webスクレイピング**
        Wikiサイトから直接取得する。
        ```bash
        python get_data.py
        ```

3.  **用語集の登録**:
    ```bash
    python add_glossary.py
    ```
    ローカルの `zzz_glossary.csv` を自動的にGoogle Cloud Storageへアップロードし、Translation APIに用語集リソースを作成する（既存の同名用語集は削除・再作成される）。

4.  **翻訳テスト**:
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
```

### 3. 設定
`data.yml` をプロジェクトルートに配置する。
```yaml
project_id: "your-project-id"
location: "us-central1"
glossary_id: "zzz-glossary"
bucket_uri: "gs://your-bucket/zzz_glossary.csv"
csv_file: "zzz_glossary.csv"
```

## ファイル構成

*   `get_data_xml.py`: XMLダンプ解析・CSV生成スクリプト (推奨)
*   `get_data.py`: Wikiスクレイピング・CSV生成スクリプト
*   `add_glossary.py`: GCSアップロードおよび用語集リソース登録スクリプト
*   `translate_test.py`: 用語集適用確認用テストスクリプト
*   `data.yml`: プロジェクト設定ファイル
*   `zzz_glossary.csv`: 生成される用語集データ（ヘッダー: `en`, `ja`）

## 制限事項・既知の問題

*   **XMLデータの鮮度**: XMLダンプを使用する場合、データの内容はダンプ作成時点のものとなる。
*   **スクレイピングの制限**: `get_data.py` を使用する場合、Fandom WikiのHTML構造変更により動作しなくなる可能性がある。
*   **データ精度**: Wikiのテーブル構造やテンプレート記述に依存するため、一部の用語で対訳が正しく抽出できない場合がある。

## 技術仕様

*   **データ抽出**: `xml.etree.ElementTree` (XML), `requests`, `BeautifulSoup4` (Web)
*   **データ処理**: `pandas`
*   **API連携**: `google-cloud-translate`
*   **設定管理**: `PyYAML`

## ライセンス

ライセンス情報は含まれていない。