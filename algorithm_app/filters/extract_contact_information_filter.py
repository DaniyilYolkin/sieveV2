import re
from copy import deepcopy
from .basic_filter import BasicFilter


class ExtractContactInformationFilter(BasicFilter):

    def __init__(self) -> None:
        super().__init__()

    def __find_phone_numbers_by_regex(self, text: str) -> list[str]:
        phone_pattern = r'\+?\d[\d -]{8,12}\d'
        found_phone_numbers = re.findall(phone_pattern, text)
        return found_phone_numbers

    def __find_emails_by_regex(self, text: str) -> list[str]:
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_website_emails = re.findall(email_pattern, text)
        return found_website_emails

    def run(self, link_objects: list[dict]) -> list[dict]:
        updated_link_objects = deepcopy(link_objects)
        for link_object in updated_link_objects:
            link_object['phone_numbers'] = self.__find_phone_numbers_by_regex(link_object['text'])
            link_object['corporate_emails'] = self.__find_emails_by_regex(link_object['text'])
        return super().run(updated_link_objects)