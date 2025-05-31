from copy import deepcopy
from .basic_filter import BasicFilter


class OccurrencesCountFilter(BasicFilter):

    def __init__(self, url_column_name: str, num_occurrences_column_name: str):
        super().__init__()
        self.__url_column_name = url_column_name
        self.__num_occurrences_column_name = num_occurrences_column_name

    def run(self, link_objects: list[dict]) -> list[dict]:
        link_domain_objects = []
        domains_processed = []
        updated_link_objects = deepcopy(link_objects)
        for link_object in updated_link_objects:
            domain_name = link_object[self.__url_column_name].split("/")[2]
            count = link_object[self.__num_occurrences_column_name]
            if not domains_processed.__contains__(domain_name):
                domains_processed.append(domain_name)
                link_domain_objects.append({'domain': domain_name, self.__num_occurrences_column_name: count})
            else:
                for link_domain_object in link_domain_objects:
                    if link_domain_object['domain'] == domain_name:
                        link_domain_object[self.__num_occurrences_column_name] += count
        return super().run(link_domain_objects)
