import ssl
import certifi
import asyncio
import aiohttp
import re
import os
import yaml
import logging

from bs4 import BeautifulSoup
from copy import deepcopy

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(APP_DIR, '..', 'config.yaml')

with open(CONFIG_FILE_PATH, 'r') as file:
    config: dict = yaml.safe_load(file)

HEADERS = config['search']['headers']

ssl._create_default_https_context = ssl._create_unverified_context
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())


class RequestAdapter:

    def __init__(self, links):
        self.links = links
        self.client_errors = 0
        self.timeout_errors = 0
        self.other_errors = 0

    def __get_website_text(self, soup: BeautifulSoup) -> dict:
        text = ' '.join([tag.text for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
        stripped_text = re.sub(r'\s+', ' ', text).strip() if text else ''
        return {
            "text_found_status": True if stripped_text else False,
            "text": stripped_text
        }

    async def __fetch_website_data(self, session: aiohttp.ClientSession, url: str) -> dict:
        title = ""
        description = ""
        text = ""
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            async with session.get(url, ssl=ssl_context, timeout=300) as response:
                html_response = await response.text()
                soup = BeautifulSoup(html_response, 'html.parser')
                website_text = self.__get_website_text(soup)['text']
                meta_description = soup.find('meta', attrs={'name': 'description'})
                title = soup.title.string if soup.title else "Title cannot be extracted"
                description = meta_description['content'] if meta_description else "Description cannot be extracted"
                text = website_text if website_text else "Text cannot be extracted"
        except aiohttp.ClientError as e:
            logging.info(f"Error fetching metadata for {url}: {e}")
            title = "Metadata cannot be extracted"
            description = "Metadata cannot be extracted"
            text = "Text cannot be extracted"
            self.client_errors += 1
        except (TimeoutError, aiohttp.ClientTimeout) as e:
            logging.info(f"Timeout error fetching metadata for {url}: {e}")
            title = "Metadata cannot be extracted"
            description = "Metadata cannot be extracted"
            text = "Text cannot be extracted"
            self.timeout_errors += 1
        except Exception as e:
            logging.info(f"Unexpected error fetching metadata for {url}: {e}")
            title = "Metadata cannot be extracted"
            description = "Metadata cannot be extracted"
            text = "Text cannot be extracted"
            self.other_errors += 1
        finally:
            return {
                "url": url if url else "URL is missing",
                "title": title if title else "Title is missing",
                "description": description if description else "Description is missing",
                "text": text if text else "Text is missing"
            }

    async def __extract_website_data_async(self) -> tuple:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            tasks = [self.__fetch_website_data(session, link) for link in self.links]
            results = await asyncio.gather(*tasks)
        return results

    def run(self) -> list[dict]:
        websites_data = asyncio.run(self.__extract_website_data_async())
        print(f"Request Adapter run finished!")
        print(f"Total errors occurred: {self.client_errors + self.timeout_errors + self.other_errors}")
        print(f"Total client occurred: {self.client_errors}")
        print(f"Total timeout occurred: {self.timeout_errors}")
        print(f"Total other errors occurred: {self.other_errors}")
        return websites_data