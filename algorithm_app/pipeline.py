from .filters import BasicFilter
from .utils import annotate, append_to_json_file


class Pipeline:
    def __init__(self, filters: list[list[int, list[int], BasicFilter]], base_link_objects: list[dict]):
        self.filters = filters
        self.base_link_objects = base_link_objects

    @annotate
    def execute_filter(self, pipeline_filter: BasicFilter, params: list[dict]) -> list[dict]:
        return pipeline_filter.run(*params)

    def run(self) -> list[dict]:
        link_objects = self.base_link_objects
        for filter_index, filter_receive_indexes, pipeline_filter in self.filters:
            params = [self.filters[index-1][2].result_link_objects if index else self.base_link_objects for index in filter_receive_indexes]
            link_objects = self.execute_filter(pipeline_filter, params)
        return link_objects