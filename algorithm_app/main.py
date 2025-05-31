from .utils import annotate, initialize_run, save_json_to_excel, read_from_json_file
from .webcrawler import SieveWebCrawler
from .analyser import SieveAnalyser
from datetime import datetime
from typing import Any, TYPE_CHECKING

import yaml
import os
import time

if TYPE_CHECKING:
    from flask_app.app import db
    from flask_sqlalchemy import SQLAlchemy
    from flask_app.app import SearchResult as SearchResultModel, SearchQuery as SearchQueryModel

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(APP_DIR, 'config.yaml')

with open(CONFIG_FILE_PATH, 'r') as file:
    config: dict = yaml.safe_load(file)

TIMESTAMP = datetime.now().strftime(config['timestamp_format'])
RUN_DIR: str = config['directories']['run_dir'].replace("{timestamp}", TIMESTAMP)
CRAWLER_DIR = f"{RUN_DIR}/{config['directories']['webcrawler_dir_name']}"
ANALYSER_DIR = f"{RUN_DIR}/{config['directories']['analyser_dir_name']}"

LOG_FILE: str = config['files']['log_file']
DRIVER_FILE: str = f"{config['directories']['driver_dir']}/{config['files']['driver_file']}"
CRAWLER_RESULTS_FILE_JSON = f"{CRAWLER_DIR}/crawled_links.json"
ANALYSER_RESULTS_FILE_JSON = f"{ANALYSER_DIR}/analysed_links.json"
CRAWLER_RESULTS_FILE_XLSX = f"{CRAWLER_DIR}/crawled_links.xlsx"
ANALYSER_RESULTS_FILE_XLSX = f"{ANALYSER_DIR}/analysed_links.xlsx"

DEFAULT_LANGUAGE: str = config['search']['default_language']

COUNTRY_MAPPING = {
    'GB': {
        'country': 'United Kingdom',
        "city": 'London',
        "language": ["English"],
    },
    'PT': {
        'country': 'Portugal',
        'city': 'Lisbon',
        'language': ['Portuguese (Brazil)'],
    },
    'ES': {
        'country': 'Spain',
        'city': 'Madrid',
        'language': ['Spanish']
    }
}


@annotate
def algorithm_crawl(location_query_mappings: dict) -> Any:
    sieve_webcrawler = SieveWebCrawler(RUN_DIR, CRAWLER_DIR, DRIVER_FILE)
    print(sieve_webcrawler.driver)
    print('Switching language to default...')
    sieve_webcrawler.switch_language(language=DEFAULT_LANGUAGE)
    print('Switching language to default done.')
    for country, location_object in location_query_mappings.items():
        for query in location_object['query']:
            location = {
                'country': country,
                'language': location_object['language'],
                'city': location_object['city']
            }
            retry = 0
            serp_links = sieve_webcrawler.search(location=location, search_query=query)
            while not serp_links and retry != 3:
                serp_links = sieve_webcrawler.search(location=location, search_query=query)
                retry += 1
            if retry == 3:
                raise Exception(f'Error searching for SERPs in {location["country"]}')
    sieve_webcrawler.quit()


@annotate
def algorithm_analyse(query_whitelist: list[str]) -> Any:
    sieve_analyser = SieveAnalyser(CRAWLER_RESULTS_FILE_JSON, ANALYSER_RESULTS_FILE_JSON, query_whitelist)
    sieve_analyser.run()


def execute_algorithm(query_id: int, db_instance: 'SQLAlchemy',
                      search_result_model: type['SearchResultModel'],
                      search_query_model: type['SearchQueryModel']
                      ) -> Any:
    query_country, query_keywords, query_whitelist = None, None, None

    try:
        retrieved_search_query = db_instance.session.get(search_query_model, query_id)
        if retrieved_search_query:
            print(f"[{os.getpid()}] Successfully fetched SearchQuery object with ID {query_id}.")
            print(f"[{os.getpid()}] Keywords: {retrieved_search_query.keywords}")
            print(f"[{os.getpid()}] Country: {retrieved_search_query.country}")
            query_country = retrieved_search_query.country
            query_keywords = retrieved_search_query.keywords
            query_whitelist = [element.strip() for element in retrieved_search_query.whitelist_words.split(',')]
        else:
            print(f"[{os.getpid()}] No SearchQuery object found with ID {query_id}.")
    except Exception as e:
        print(f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] ERROR fetching SearchQuery object with ID {query_id}: {e}")

    location_query_mappings = {
        COUNTRY_MAPPING[query_country]['country']: {
            'city': COUNTRY_MAPPING[query_country]['city'],
            'language': COUNTRY_MAPPING[query_country]['language'],
            'query': [query_keywords]
        }
    }

    print(location_query_mappings)
    print(query_whitelist)

    json_format = 'ndjson'
    initialize_run(RUN_DIR, CRAWLER_DIR, ANALYSER_DIR, LOG_FILE)
    algorithm_crawl(location_query_mappings)
    algorithm_analyse(query_whitelist)
    save_json_to_excel(CRAWLER_RESULTS_FILE_JSON, CRAWLER_RESULTS_FILE_XLSX, json_format)
    save_json_to_excel(ANALYSER_RESULTS_FILE_JSON, ANALYSER_RESULTS_FILE_XLSX, json_format)

    if os.path.exists(ANALYSER_RESULTS_FILE_XLSX):
        print(f"[{os.getpid()}] Saving result path to DB for query_id: {query_id}. Path: {ANALYSER_RESULTS_FILE_XLSX}")
        try:
            new_result_entry = search_result_model(
                query_id=query_id,
                website_url=ANALYSER_RESULTS_FILE_XLSX,
                description="Algorithm analysis result file",
                country=None
            )
            db_instance.session.add(new_result_entry)
            db_instance.session.commit()
            print(f"[{os.getpid()}] Successfully saved path to search_result table for query_id: {query_id}")
        except Exception as e:
            db_instance.session.rollback()
            print(f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] ERROR saving to search_result for query_id {query_id}: {e}")
            raise


def main_flask_async(query_id: int, db_instance: 'SQLAlchemy', search_result_model: type['SearchResultModel'], search_query_model: type['SearchQueryModel']) -> Any:
    """
    Main function for the algorithm processing.
    This function will be called asynchronously.
    """
    print(f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] Algorithm processing started for query_id: {query_id}")
    query_to_update = None
    try:
        query_to_update = db_instance.session.get(search_query_model, query_id)
        if not query_to_update:
            print(
                f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] ERROR: SearchQuery with id {query_id} not found. Cannot update status.")
            return

        query_to_update.status = 'processing'
        db_instance.session.commit()

        execute_algorithm(query_id, db_instance, search_result_model, search_query_model)

        query_to_update.status = 'completed'
        print(f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] Algorithm processing COMPLETED for query_id: {query_id}")

    except Exception as e:
        print(f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] ERROR during algorithm processing for query_id {query_id}: {e}")
        if query_to_update:
            query_to_update.status = 'failed'

    finally:
        if db_instance.session.is_active:
            try:
                db_instance.session.commit()
            except Exception as commit_exc:
                print(f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] ERROR committing final status for query_id {query_id}: {commit_exc}")
                db_instance.session.rollback()
        else:
            print(f"[{os.getpid()}-{time.strftime('%H:%M:%S')}] WARNING: DB session not active, cannot commit final status for query_id {query_id}")

