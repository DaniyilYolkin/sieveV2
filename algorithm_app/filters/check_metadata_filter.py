from copy import deepcopy
from .basic_filter import BasicFilter


class CheckMetadataFilter(BasicFilter):

    def __init__(self, metadata_words_whitelist: list[str]) -> None:
        super().__init__()
        self.__metadata_words_whitelist = metadata_words_whitelist

    def __is_text_containing_whitelist_words(self, text: str) -> bool:
        return any(whitelist_word in text for whitelist_word in self.__metadata_words_whitelist)

    def run(self, link_objects: list[dict]) -> list[dict]:
        updated_link_objects = deepcopy(link_objects)
        for link_object in updated_link_objects:
            link_object["metadata_contains_key_words"] = "True" if self.__is_text_containing_whitelist_words(link_object['title'].lower()) or self.__is_text_containing_whitelist_words(link_object['description'].lower()) else "False"
        return super().run(updated_link_objects)
