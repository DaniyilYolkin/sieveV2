from copy import deepcopy
from .basic_filter import BasicFilter


class RegularizeLinksFilter(BasicFilter):

    def __init__(self, url_column_name: str, replace_string: str):
        super().__init__()
        self.__url_column_name = url_column_name
        self.__replace_string = replace_string

    def run(self, link_objects: list[dict]) -> list[dict]:
        filtered_link_objects = []
        updated_link_objects = deepcopy(link_objects)
        for link_object in updated_link_objects:
            link_object[self.__url_column_name ] = link_object[self.__url_column_name ].replace(self.__replace_string, '')
            filtered_link_objects.append(link_object)
        return super().run(filtered_link_objects)