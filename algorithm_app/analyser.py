from .utils import annotate, append_to_json_file, read_from_ndjson_file
from .pipeline import Pipeline
from .filters import *

import os
import yaml

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(APP_DIR, 'config.yaml')

with open(CONFIG_FILE_PATH, 'r') as file:
    config: dict = yaml.safe_load(file)

URL_COLUMN_NAME = config['analyser']['url_column_name']
NUM_OCCURRENCES_COLUMN_NAME = config['analyser']['num_occurrences_column_name']
LOCATION_COLUMN_NAME = config['analyser']['location_column_name']


class SieveAnalyser:
    def __init__(self, links_filepath, analyser_results_filepath, whitelist_words):
        self.links_filepath = links_filepath
        self.whitelist_words = whitelist_words
        self.links_objects = read_from_ndjson_file(links_filepath)
        self.analyser_results_filepath = analyser_results_filepath

    @annotate
    def run(self):
        filters = [
            [1, [0], RegularizeLinksFilter(URL_COLUMN_NAME, 'www.')],
            [2, [1], OccurrencesCountFilter(URL_COLUMN_NAME, NUM_OCCURRENCES_COLUMN_NAME)],
            [3, [1], LocationGroupingFilter(URL_COLUMN_NAME, LOCATION_COLUMN_NAME)],
            [4, [3], BlacklistFilter(URL_COLUMN_NAME)],
            [5, [4], DeduplicationFilter(URL_COLUMN_NAME)],
            [6, [5, 2], MatchOccurrencesCountFilter(URL_COLUMN_NAME, NUM_OCCURRENCES_COLUMN_NAME, LOCATION_COLUMN_NAME)],
            [7, [6], WebsiteDataExtractionFilter(URL_COLUMN_NAME, NUM_OCCURRENCES_COLUMN_NAME, LOCATION_COLUMN_NAME)],
            [8, [7], ExtractContactInformationFilter()],
            [9, [8], TranslationFilter(URL_COLUMN_NAME)],
            [10, [9], CheckMetadataFilter(self.whitelist_words)],
        ]
        pipeline = Pipeline(filters, self.links_objects)
        append_to_json_file(pipeline.run(), self.analyser_results_filepath)
