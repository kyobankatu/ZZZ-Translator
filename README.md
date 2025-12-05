# ZZZ-Translator

## プロジェクト概要
「Zenless Zone Zero」の用語集を作成し、Google Cloud Translation APIを利用して高精度な翻訳を行うためのツールセット。WebスクレイピングやXMLデータから用語を抽出し、カスタム用語集としてGCPに登録、翻訳テストを行うまでの一連のフローを提供する。

## 主要機能
- **用語データ収集**: WikiからのスクレイピングおよびXMLダンプからの用語抽出
- **データ統合**: 複数のソースから取得した用語データを結合・重複排除
- **用語集管理**: Google Cloud StorageへのアップロードとTranslation API用語集リソースの作成
- **翻訳テスト**: 作成した用語集を使用した翻訳精度の検証

## 使用方法

### 1. データ収集
WebサイトまたはXMLファイルから用語データを取得する。
```bash
# Webスクレイピングによる取得
python src/get_data_scraping.py

# XMLファイルからの抽出
python src/get_data_xml.py
```

### 2. データの結合
収集したCSVファイルを結合し、マスターデータを作成する。
```bash
python src/conbine_glossary.py
```

### 3. 用語集の登録
作成した用語集をGoogle Cloudにアップロードし、APIで使用可能な状態にする。
```bash
python src/add_glossary.py
```

### 4. 翻訳テスト
用語集が正しく機能しているか確認する。
```bash
# ランダムな用語でテスト
python src/translate_test.py

# 特定の単語をテスト
python src/translate_test.py "翻訳したいテキスト"
```

## 動作環境
- Python 3.x
- Google Cloud Platform アカウントとプロジェクト
- Google Cloud Translation API (Advanced) の有効化

## インストール・実行方法

1. **リポジトリのクローン**
2. **依存ライブラリのインストール**
   ```bash
   pip install pandas google-cloud-translate google-cloud-storage beautifulsoup4 requests pyyaml
   ```
3. **Google Cloud認証設定**
   サービスアカウントキーを取得し、環境変数を設定する。
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account-file.json"
   ```
   (Windows PowerShellの場合)
   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="path\to\your-service-account-file.json"
   ```
4. **設定ファイルの編集**
   `resource/data.yml` を環境に合わせて編集する（Project ID, GCS Bucket URIなど）。

## ファイル構成
- `src/`
  - `get_data_scraping.py`: Webスクレイピング用スクリプト
  - `get_data_xml.py`: XML解析・抽出用スクリプト
  - `conbine_glossary.py`: CSV結合用スクリプト
  - `add_glossary.py`: GCP用語集登録スクリプト
  - `translate_test.py`: 翻訳テストスクリプト
- `resource/`
  - `data.yml`: プロジェクト設定ファイル
  - `*.csv`: 生成された用語集データ
  - `*.xml`: 解析元のXMLデータ

## 制限事項・既知の問題
- `conbine_glossary.py` 内の入力ファイル名はコード内で指定されており、`data.yml` の設定とは独立している場合がある。
- Google Cloud Translation API (Advanced) の利用には課金が発生する場合がある。
- スクレイピング対象サイトの構造変更により、`get_data_scraping.py` が動作しなくなる可能性がある。

## 技術仕様
- **言語**: Python
- **ライブラリ**: Pandas, BeautifulSoup4, Google Cloud Client Libraries
- **データ形式**: CSV, XML, YAML

## ライセンス
MIT License