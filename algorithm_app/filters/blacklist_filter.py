from copy import deepcopy
from .basic_filter import BasicFilter

import os
import yaml

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(APP_DIR, '..', 'config.yaml')

with open(CONFIG_FILE_PATH, 'r') as file:
    config: dict = yaml.safe_load(file)

BLACKLIST_WORDS = config['blacklist_filter']['link_words']


class BlacklistFilter(BasicFilter):

    def __init__(self, url_column_name: str):
        super().__init__()
        self.__url_column_name = url_column_name

    def __is_containing_blacklist_words(self, link: str) -> bool:
        return any(blacklist_word in link for blacklist_word in BLACKLIST_WORDS)

    def run(self, link_objects: list[dict]) -> list[dict]:
        updated_link_objects = deepcopy(link_objects)
        return super().run([link_object for link_object in updated_link_objects if not self.__is_containing_blacklist_words(link_object[self.__url_column_name])])
