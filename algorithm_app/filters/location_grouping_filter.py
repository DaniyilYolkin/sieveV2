from copy import deepcopy
from .basic_filter import BasicFilter


class LocationGroupingFilter(BasicFilter):
    def __init__(self, url_column_name: str, location_column_name: str):
        super().__init__()
        self.__url_column_name = url_column_name
        self.__location_column_name = location_column_name

    def run(self, link_objects: list[dict]) -> list[dict]:
        filtered_objects = deepcopy(link_objects)
        for index, link_object in enumerate(filtered_objects):
            link_url = link_object[self.__url_column_name]
            link_domain_name = link_url.split("/")[2]
            filtered_objects[index][self.__location_column_name] = [link_object[self.__location_column_name]]
            for self_link_object in link_objects:
                self_link_url = self_link_object[self.__url_column_name]
                self_link_domain_name = self_link_url.split("/")[2]
                if link_domain_name == self_link_domain_name \
                        and link_url != self_link_url\
                        and not link_object[self.__location_column_name].__contains__(self_link_object[self.__location_column_name]):
                    link_object[self.__location_column_name].append(self_link_object[self.__location_column_name])
        return super().run(filtered_objects)