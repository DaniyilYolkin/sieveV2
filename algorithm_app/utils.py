import re
from typing import Any

import os
import time
import json
import logging
import pandas as pd


def annotate(func) -> Any:
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            result = None
        end_time = time.time()
        print(f'Total time taken for {func.__name__} - {end_time-start_time} seconds')
        logging.info(f'Total time taken for {func.__name__} - {end_time-start_time} seconds')
        return result
    return wrapper


@annotate
def initialize_run(run_dir: str, webcrawler_dir: str, analyser_dir: str, log_file: str) -> Any:
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(webcrawler_dir, exist_ok=True)
    os.makedirs(analyser_dir, exist_ok=True)
    logging.basicConfig(filename=f'{run_dir}/{log_file}', level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s')


@annotate
def append_to_json_file(data: list[dict], filepath: str) -> Any:
    try:
        with open(filepath, 'a') as file:
            for row in data:
                json.dump(row, file)
                file.write('\n')
    except Exception as e:
        print(f"Error writing to the JSON file: {e}")


@annotate
def read_from_ndjson_file(filepath: str) -> list[dict]:
    data = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                data.append(json.loads(line))
    except Exception as e:
        print(f"Error reading the JSON file: {e}")
    finally:
        return data


@annotate
def read_from_json_file(filepath: str) -> dict:
    data = ''
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        print(f"Error reading the JSON file: {e}")
    finally:
        return data


def clean_text(text):
    return re.sub(r'[^\x20-\x7E]', '', text)


def clean_dataframe(df):
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: clean_text(x) if isinstance(x, str) else x)
    return df


@annotate
def save_json_to_excel(json_filepath: str, excel_filepath: str, json_format: str) -> Any:
    if json_format == 'json':
        data = read_from_json_file(json_filepath)
        df = pd.DataFrame(data)
        df = clean_dataframe(df)
        df.to_excel(excel_filepath, index=False)
    elif json_format == 'ndjson':
        data = read_from_ndjson_file(json_filepath)
        df = pd.DataFrame(data)
        df = clean_dataframe(df)
        df.to_excel(excel_filepath, index=False)
    else:
        logging.warning('Error during saving json file to excel: JSON format is not supported')
