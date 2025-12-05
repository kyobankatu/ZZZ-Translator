import pandas as pd

def combine_glossaries():
    # CSVファイルのパス
    csv_files = [
        'resource/zzz_glossary.csv',
        'resource/zzz_glossary_scraping.csv',
        'resource/zzz_glossary_xml.csv'
    ]
    
    combined_data = []

    for file in csv_files:
        try:
            # CSVファイルを読み込む
            df = pd.read_csv(file)
            combined_data.append(df)
        except Exception as e:
            print(f"エラー: {file} の読み込みに失敗しました。\n{e}")

    if combined_data:
        # データを結合
        combined_df = pd.concat(combined_data, ignore_index=True)
        
        # 重複を削除
        combined_df.drop_duplicates(subset=['en', 'ja'], inplace=True)

        # 結合したデータを新しいCSVファイルに保存
        combined_df.to_csv('resource/combined_glossary.csv', index=False, encoding='utf-8')
        print("結合した用語集を resource/combined_glossary.csv に保存しました。")
    else:
        print("結合するデータがありませんでした。")

if __name__ == "__main__":
    combine_glossaries()