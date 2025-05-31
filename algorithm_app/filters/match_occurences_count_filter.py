from copy import deepcopy
from .basic_filter import BasicFilter


class MatchOccurrencesCountFilter(BasicFilter):

    def __init__(self, url_column_name: str, num_occurrences_column_name: str, location_column_name: str):
        super().__init__()
        self.__url_column_name = url_column_name
        self.__num_occurrences_column_name = num_occurrences_column_name
        self.__location_column_name = location_column_name

    def run(self, link_objects: list[dict], domain_occurrences_objects: list[dict]) -> list[dict]:
        filtered_link_objects = []
        updated_link_objects = deepcopy(link_objects)
        for link_object in updated_link_objects:
            link_domain_name = link_object[self.__url_column_name].split("/")[2]
            for domain_occurrences_object in domain_occurrences_objects:
                if domain_occurrences_object['domain'] == link_domain_name:
                    filtered_link_objects.append(
                        {
                            self.__location_column_name: link_object[self.__location_column_name],
                            self.__url_column_name: link_object[self.__url_column_name],
                            self.__num_occurrences_column_name: domain_occurrences_object[self.__num_occurrences_column_name]
                        }
                    )
                    break
        return super().run(filtered_link_objects)