# ZZZ-Translator

## プロジェクト概要
「Zenless Zone Zero」の用語集を作成し、Google Cloud Translation APIを利用して高精度な翻訳を行うためのツールセット。WebスクレイピングやXMLデータから用語を抽出し、AIによるクリーニングを経てカスタム用語集としてGCPに登録、翻訳テストを行うまでの一連のフローを提供する。

## 主要機能
- **用語データ収集**: WikiからのスクレイピングおよびXMLダンプからの用語抽出
- **データ統合・クリーニング**: 複数のソースから取得した用語データを結合し、Gemini APIを用いて不要な読み仮名や注釈を除去
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

### 2. データの結合とクリーニング
収集したCSVファイルを結合し、AIを用いてデータをクリーニングしてマスターデータを作成する。
※Gemini APIキーの設定が必要
```bash
python src/combine_glossary.py
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
python src/translate_test.py "翻訳したいテキスト(基本的には単語を想定)"
```

## 動作環境
- Python 3.x
- Google Cloud Platform アカウントとプロジェクト
- Google Cloud Translation API (Advanced) の有効化
- Google Gemini API の有効化（データクリーニング用）

## インストール・実行方法

1. **リポジトリのクローン**
2. **依存ライブラリのインストール**
   ```bash
   pip install -r requirements.txt
   ```
3. **Google Cloud認証設定**
   Google Cloud CLI (`gcloud`) をインストールし、認証を行う。
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
4. **Gemini APIキーの設定**
   データクリーニング機能を使用するために環境変数を設定する。
   ```powershell
   $env:GOOGLE_API_KEY="your-gemini-api-key"
   ```
5. **設定ファイルの編集**
   `resource/data.yml` を環境に合わせて編集する（Project ID, GCS Bucket URIなど）。

## ファイル構成
- `src/`
  - `get_data_scraping.py`: Webスクレイピング用スクリプト
  - `get_data_xml.py`: XML解析・抽出用スクリプト
  - `combine_glossary.py`: CSV結合・AIクリーニング用スクリプト
  - `add_glossary.py`: GCP用語集登録スクリプト
  - `translate_test.py`: 翻訳テストスクリプト
- `resource/`
  - `data.yml`: プロジェクト設定ファイル
  - `*.csv`: 生成された用語集データ
  - `*.xml`: 解析元のXMLデータ

## 制限事項・既知の問題
- `combine_glossary.py` のAIクリーニング機能は、Gemini APIのレート制限（1分あたり10リクエスト等）を考慮して低速に動作するように設計されている。
- Google Cloud Translation API (Advanced) および Gemini API の利用には課金が発生する場合がある。
- スクレイピング対象サイトの構造変更により、`get_data_scraping.py` が動作しなくなる可能性がある。

## 技術仕様
- **言語**: Python
- **ライブラリ**: Pandas, BeautifulSoup4, Google Cloud Client Libraries, Google Generative AI SDK
- **データ形式**: CSV, XML, YAML

## ライセンス

### ソースコード
**Polyform Noncommercial License 1.0.0**

本プロジェクトのソースコードは、**非営利目的でのみ**利用可能です。商用利用は固く禁止されています。
詳細: [Polyform Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)

### 用語データ
本ツールによって生成・抽出された用語データ（CSVファイル等）は、その元となるデータソース（Wiki等）のライセンスに従います。
- **Zenless Zone Zero Wiki (Fandom)**: [CC BY-SA](https://www.fandom.com/licensing) (Creative Commons Attribution-ShareAlike)

※ 本ツールは非公式のファンメイドプロジェクトであり、HoYoverse等の権利者とは一切関係ありません。