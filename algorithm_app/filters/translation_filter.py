import asyncio
from copy import deepcopy
import logging
import string
from .basic_filter import BasicFilter


class TranslationFilter(BasicFilter):

    def __init__(self, url_column_name: str, concurrency_limit: int = 50) -> None:
        super().__init__()
        self.__url_column_name = url_column_name
        from googletrans import Translator
        self._translator = Translator(service_urls=['translate.googleapis.com'])
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        logging.info(f"TranslationFilter initialized with concurrency limit: {concurrency_limit}")

    def __remove_punctuation(self, text: str) -> str:
        return "".join([char for char in text if char not in string.punctuation])

    async def __async_translate_text(self, text_object: dict) -> dict:
        async with self._semaphore:
            updated_object = deepcopy(text_object)
            original_text = updated_object.get('text')
            if not original_text or not isinstance(original_text, str) or not original_text.strip():
                updated_object['text'] = 'Original text was empty or invalid'
                return updated_object
            logging.debug(f"Semaphore acquired. Translating: '{original_text[:50]}...'")
            try:
                translated_obj = await self._translator.translate(original_text, dest='en')
                translated_text_content = translated_obj.text
                updated_object[
                    'text'] = translated_text_content if translated_text_content else 'Translation resulted in empty text'
            except Exception as e:
                logging.warning(f"Error translating text (first 50 chars: '{original_text[:50]}...') occurred: {e}")
                updated_object['text'] = "Translation failed"
            return updated_object

    async def __async_batch_translate_texts(self, text_objects: list[dict]) -> list[dict]:
        if not text_objects:
            return []
        tasks = [self.__async_translate_text(text_object) for text_object in text_objects]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    async def _orchestrate_all_translations(self, titles_data: list[dict], descriptions_data: list[dict]) -> tuple[
        list[dict], list[dict]]:
        """Orchestrates title and description translations within a single async context."""
        translated_titles_list = []
        translated_descriptions_list = []

        if titles_data:
            logging.info(f"Orchestrating translation for {len(titles_data)} titles.")
            translated_titles_list = await self.__async_batch_translate_texts(titles_data)

        if descriptions_data:
            logging.info(f"Orchestrating translation for {len(descriptions_data)} descriptions.")
            translated_descriptions_list = await self.__async_batch_translate_texts(descriptions_data)

        return translated_titles_list, translated_descriptions_list

    def run(self, link_objects: list[dict]) -> list[dict]:
        if not link_objects:
            logging.info("No link objects to process.")
            return []
        updated_link_objects = deepcopy(link_objects)

        titles_data = [
            {
                self.__url_column_name: link_object[self.__url_column_name],
                'text': self.__remove_punctuation(link_object['title'])
            } for link_object in updated_link_objects if
            link_object.get('title') and link_object.get(self.__url_column_name)
        ]
        descriptions_data = [
            {
                self.__url_column_name: link_object[self.__url_column_name],
                'text': self.__remove_punctuation(link_object['description'])
            } for link_object in updated_link_objects if
            link_object.get('description') and link_object.get(self.__url_column_name)
        ]

        translated_titles_list = []
        translated_descriptions_list = []

        try:
            current_loop = asyncio.get_running_loop()
            if current_loop.is_running():
                logging.error("TranslationFilter.run() was called from an already running event loop. "
                              "This method should be made 'async def' or called from a synchronous context.")

        except RuntimeError:
            pass

        if titles_data or descriptions_data:
            try:
                logging.info("Starting orchestrated translations.")
                translated_titles_list, translated_descriptions_list = asyncio.run(
                    self._orchestrate_all_translations(titles_data, descriptions_data)
                )
                logging.info("Finished orchestrated translations.")
            except Exception as e:
                logging.error(f'Error occurred during orchestrated translations: {e}')
        else:
            logging.info("No titles or descriptions to translate.")

        translated_titles_map = {
            item[self.__url_column_name]: item['text']
            for item in translated_titles_list if
            isinstance(item, dict) and self.__url_column_name in item and 'text' in item
        }
        translated_descriptions_map = {
            item[self.__url_column_name]: item['text']
            for item in translated_descriptions_list if
            isinstance(item, dict) and self.__url_column_name in item and 'text' in item
        }
        for link_object in updated_link_objects:
            url = link_object.get(self.__url_column_name)
            if not url: continue
            if url in translated_titles_map: link_object['title'] = translated_titles_map[url]
            if url in translated_descriptions_map: link_object['description'] = translated_descriptions_map[url]

        return super().run(updated_link_objects)