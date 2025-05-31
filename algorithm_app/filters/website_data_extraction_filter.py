from copy import deepcopy
from .basic_filter import BasicFilter
from .request_adapter import RequestAdapter

import re


class WebsiteDataExtractionFilter(BasicFilter):

    def __init__(self, url_column_name: str, num_occurrences_column_name: str, location_column_name: str):
        super().__init__()
        self.__url_column_name = url_column_name
        self.__num_occurrences_column_name = num_occurrences_column_name
        self.__location_column_name = location_column_name

    def __clean_text(self, text):
        return re.sub(r'[^\x20-\x7E]', '', text)

    def run(self, link_objects: list[dict]) -> list[dict]:
        updated_link_objects = deepcopy(link_objects)
        urls = [link_object[self.__url_column_name] for link_object in updated_link_objects]
        request_adapter = RequestAdapter(urls)
        website_data_results = request_adapter.run()
        for website_data in website_data_results:
            url = website_data[self.__url_column_name]
            title = self.__clean_text(website_data['title'])
            description = self.__clean_text(website_data['description'])
            text = self.__clean_text(website_data['text'])
            for link_object in updated_link_objects:
                if link_object[self.__url_column_name] == url:
                    link_object['title'] = title
                    link_object['description'] = description
                    link_object['text'] = text # f"{text[:500]}..." if len(text) > 500 else text

        return super().run(updated_link_objects)