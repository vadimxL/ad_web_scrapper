import json
import pandas as pd


def open_json(fn):
    # fn = 'parsed_yad2_2023-07-30_22-24-35'
    with open(fn + '.json', 'r', encoding='utf-8') as f1:
        jd = json.loads(f1.read())
        return jd, fn


def normalize_json(json_data_: json, file_name_: str):
    # normalizing
    df = pd.json_normalize(json_data_)
    with open(file_name_ + ".csv", 'w') as f:
        df.to_csv(f, index=False, header=True, encoding='utf-8-sig')


if __name__ == '__main__':
    fn = 'json/parsed_results'
    json_data, file_name = open_json(fn)
    normalize_json(json_data, file_name)
