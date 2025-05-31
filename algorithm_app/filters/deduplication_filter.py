from copy import deepcopy
from .basic_filter import BasicFilter


class DeduplicationFilter(BasicFilter):
    def __init__(self, url_column_name: str):
        super().__init__()
        self.__url_column_name = url_column_name

    def run(self, link_objects: list[dict]) -> list[dict]:
        deduplicated_link_objects = []
        checked_domains = []
        updated_link_objects = deepcopy(link_objects)
        for link_object in updated_link_objects:
            link_domain_name = link_object[self.__url_column_name].split("/")[2]
            if not checked_domains.__contains__(link_domain_name):
                deduplicated_link_objects.append(link_object)
                checked_domains.append(link_domain_name)
        return super().run(deduplicated_link_objects)
