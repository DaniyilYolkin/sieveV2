import os

from .utils import append_to_json_file, annotate
from typing import Any
from selenium import webdriver
from selenium.common import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC

import yaml
import logging
import time
import urllib.parse
import base64

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(APP_DIR, 'config.yaml')

with open(CONFIG_FILE_PATH, 'r') as file:
    config: dict = yaml.safe_load(file)

DEFAULT_LANGUAGE: str = config['search']['default_language']
SEARCH_PAGES: int = config['search']['search_pages']
WEBSITE: str = config['search']['website']
HEADLESS_MODE: bool = config['search']['headless_mode']


class SieveWebCrawler:

    def __init__(self, run_dir, res_dir, driver_file=None):
        self.driver = None
        self.driver_file = driver_file
        self.get_driver()
        self.run_dir = run_dir
        self.res_dir = res_dir

    @annotate
    def install_driver(self) -> None:
        ChromeDriverManager().install()
        os.chmod("/root/.wdm/drivers/chromedriver/linux64/127.0.6533.72/chromedriver-linux64/chromedriver", 0o755)

    @annotate
    def _get_driver_path(self) -> str | None:
        """
        Installs (if necessary) and returns the path to the ChromeDriver.
        Optionally attempts to set execute permissions on non-Windows OS.
        """
        try:
            driver_path = ChromeDriverManager().install()
            if os.name != 'nt':
                try:
                    os.chmod(driver_path, 0o755)
                    logging.info(f"Ensured execute permissions for ChromeDriver at {driver_path}")
                except OSError as e:
                    logging.warning(f"Could not set execute permissions for {driver_path}: {e}. "
                                    "This might be okay if permissions are already correct.")
            return driver_path
        except Exception as e:
            logging.error(f"ChromeDriverManager().install() failed: {e}")
            return None

    @annotate
    def get_options(self) -> Options:
        options = None
        try:
            options = Options()
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1200')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            if HEADLESS_MODE:
                options.add_argument('--headless')
        except Exception as e:
            logging.warning(f"Exception occurred in get_options: {e}")
            print(f"Exception occurred in get_options: {e}")
        finally:
            return options

    @annotate
    def get_service(self) -> Service:
        service = None
        try:
            service = Service(executable_path="/root/.wdm/drivers/chromedriver/linux64/127.0.6533.72/chromedriver-linux64/chromedriver")
        except Exception as e:
            logging.warning(f"Exception occurred in get_service: {e}")
            print(f"Exception occurred in get_service: {e}")
        finally:
            return service

    @annotate
    def get_driver(self):
        """Initializes and configures the Chrome WebDriver."""
        driver_path = None
        try:
            options = self.get_options()
            if not options:
                raise RuntimeError("Failed to retrieve Chrome options. WebDriver cannot be initialized.")

            driver_path = self._get_driver_path()
            if not driver_path:
                raise RuntimeError("Failed to get ChromeDriver path. WebDriver cannot be initialized.")

            service = Service(executable_path=driver_path)

            self.driver = webdriver.Chrome(options=options, service=service)

            print('Init - Redirecting to main website...')
            self.redirect_to_website(WEBSITE)
            print('Init - Redirecting to main website complete')
            print('Init - Switching off redirection...')
            self.switch_off_redirection()
            print('Init - Switching off redirection complete')
        except Exception as e:
            logging.warning(f'{e}')
            print(f'{e}')

    def _decode_bing_url(self, bing_url: str) -> str:
        """Decodes a Bing tracking URL to get the actual destination URL."""
        try:
            if bing_url and "bing.com/ck/a" in bing_url:
                parsed_url = urllib.parse.urlparse(bing_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)

                u_param_list = query_params.get('u')
                if not u_param_list:
                    return bing_url

                u_param = u_param_list[0]

                if u_param and u_param.startswith('a1'):
                    encoded_url_part = u_param[2:]

                    padding_needed = len(encoded_url_part) % 4
                    if padding_needed:
                        encoded_url_part += '=' * (4 - padding_needed)

                    decoded_bytes = base64.b64decode(encoded_url_part)
                    return decoded_bytes.decode('utf-8')
            return bing_url
        except Exception as e:
            logging.warning(f"Failed to decode Bing URL '{bing_url}': {e}")
            return bing_url

    def switch_off_redirection(self):
        self.open_location_settings()
        checkbox = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='newwnd']"))
        )
        if checkbox.is_selected():
            print('Redirect checkbox is checked! Unchecking...')
            checkbox.click()

    def redirect_to_website(self, website: str = "https://www.bing.com", wait_time: int = 1) -> Any:
        self.driver.get(website)
        time.sleep(wait_time)

    def click_element(self, by, value, retry_attempt: int = 0, wait_time: int = 2) -> Any:
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by, value))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((by, value))
            )
            element.click()
            time.sleep(wait_time)
        except ElementClickInterceptedException as e:
            if retry_attempt < 3:
                logging.warning(f"Element click intercepted, retrying... Attempt: {retry_attempt + 1}")
                time.sleep(wait_time)
                self.take_screenshot(f"click_element_error_attempt_{retry_attempt}")
                try:
                    self.decline_cookies()
                except e:
                    logging.info(f'Reject cookies button is not found')
                self.click_element(by, value, retry_attempt + 1)
            else:
                logging.error(f"Max retry attempts reached for clicking element: {e}")
                self.take_screenshot("click_element_error")
                raise
        except Exception as e:
            logging.error(f"Error clicking element: {e}")
            self.take_screenshot("click_element_error")
            raise

    def generate_new_url(self, url: str, current_position: int, increment: int) -> str:
        if not url:
            url = '&'.join(
                [f'first={current_position + increment}' if element.__contains__('first=') else element for element in
                 url.split('&')])
        else:
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//a[contains(@title, 'Next page')]"))
            )
            url = '&'.join(
                [f'first={current_position + increment}' if element.__contains__('first=') else element for element in
                 next_button.get_attribute('href').split('&')])
        return url

    def switch_language(self, language: str) -> Any:
        try:
            print(language)
            print('Redirecting to the website')
            self.redirect_to_website()
            print('Clicking ID')
            self.click_element(By.ID, "id_sc")
            print('Clicking selector')
            self.click_element(By.CSS_SELECTOR, "div#hbsettings")
            print('Clicking XPATH 1')
            self.click_element(By.XPATH, "//a[contains(@href, 'region_section#region-section')]")
            print('Clicking XPATH 2')
            self.click_element(By.XPATH, f"//li[.//div[text()='{language}']]//a")
        except Exception as e:
            logging.error(f'Error occurred: {e}')
            print(e)

    def enter_search_query(self, search_query: str, wait_time: int = 1) -> Any:
        search_box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.click()

        time.sleep(wait_time)

        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)

        time.sleep(wait_time)

    def open_location_settings(self) -> Any:
        self.click_element(By.ID, "id_sc")
        self.click_element(By.CSS_SELECTOR, "div#hbsettings")
        self.click_element(By.XPATH, "//a[contains(@href, 'region_section#region-section')]")

    def switch_search_city(self, city: str, wait_time: int = 2) -> Any:
        self.redirect_to_website()
        self.open_location_settings()
        city_search_box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='text' and (@placeholder='Enter city, address or postcode' or @placeholder='Enter city, address or zip code')]"))
        )
        city_search_box.clear()
        city_search_box.click()
        time.sleep(wait_time)
        city_search_box.send_keys(city)
        time.sleep(wait_time)
        city_search_box.send_keys(Keys.RETURN)
        time.sleep(wait_time)
        self.click_element(By.XPATH, "//input[@type='submit' and @id='sv_btn']")

    def switch_search_result_language(self, languages: list[str]) -> Any:
        self.redirect_to_website()
        self.open_location_settings()
        self.click_element(By.XPATH, "//input[@id='preferuilang']")
        self.click_element(By.XPATH, "//input[@type='submit' and @id='sv_btn']")
        self.open_location_settings()
        is_language_changed = False
        for index, language in enumerate(languages):
            if language != 'English':
                if index == 0:
                    self.click_element(By.XPATH, "//input[@id='langlimit']")
                    self.click_element(By.XPATH, "//div[@id='search-languages-seemore-btn']//a[contains(text(), 'See more languages')]")
                label_xpath = f"//label[contains(text(), '{language}')]"
                label_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, label_xpath))
                )
                self.click_element(By.XPATH, f"//input[@type='checkbox' and @id='{label_element.get_attribute('for')}']")
                is_language_changed = True
        if is_language_changed:
            self.click_element(By.XPATH, "//input[@type='submit' and @id='sv_btn']")

    def switch_search_country(self, country: str, wait_time: int = 1) -> Any:
        self.redirect_to_website()
        self.open_location_settings()
        time.sleep(wait_time)
        self.click_element(By.XPATH, "//a[contains(text(), 'See more countries/regions')]")
        time.sleep(wait_time)
        self.click_element(By.XPATH, f"//a[text()='{country}']")

    def switch_search_location(self, location_object: dict) -> Any:
        try:
            city, languages, country = location_object['city'], location_object['language'], location_object['country']
            print(f'Switching search country to {country}')
            self.switch_search_country(country)
            print(f'Switching search languages to {languages}')
            self.switch_search_result_language(languages)
            print(f'Switching search city to {city}')
            self.switch_search_city(city)
        except Exception as e:
            raise Exception(f"Error during switching location: {e}")

    def decline_cookies(self, cookie_reject_button_class: str = "bnp_btn_reject") -> Any:
        try:
            reject_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, cookie_reject_button_class))
            )
            reject_button.click()
        except TimeoutException:
            logging.info("Reject button doesn't exist!")

    def take_screenshot(self, name: str) -> Any:
        self.driver.save_screenshot(f"{self.run_dir}/{name}.png")

    def scroll_to_bottom(self, wait_time: int = 2) -> Any:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_time)

    def search(self, location: dict, search_query: str) -> list[dict]:
        self.switch_search_location(location)
        self.redirect_to_website(WEBSITE)
        time.sleep(1)
        self.enter_search_query(search_query)
        time.sleep(1)
        self.decline_cookies()
        time.sleep(1)
        link_objects: list[dict] = []
        urls_processed: list = []
        current_search_page = 1
        while current_search_page <= SEARCH_PAGES:
            time.sleep(1)
            results = self.driver.find_elements(By.CSS_SELECTOR, "li.b_algo h2 a")
            logging.info([result.get_attribute("href") for result in results])
            print(f"Current search page: {current_search_page}")
            for result in results:
                link = self._decode_bing_url(result.get_attribute("href"))
                if link:
                    domain_part = link.split("/")[2]
                    if not urls_processed.__contains__(domain_part):
                        link_objects.append({'url': link, 'num_occurrences': 1})
                        urls_processed.append(domain_part)
                    else:
                        for link_object in link_objects:
                            if link_object['url'].__contains__(domain_part):
                                link_object['num_occurrences'] += 1
                                break
            print([link_object['url'] for link_object in link_objects])

            try:
                self.scroll_to_bottom()
                self.take_screenshot("next_button_click_before")
                self.click_element(By.XPATH, f"//a[contains(@title, 'Next page')]", wait_time=1)
                current_search_page += 1
                self.take_screenshot("next_button_click_after")
            except TimeoutException as e:
                self.take_screenshot("next_button_error")
                logging.error(f'Error occurred: {e}')
                break
        append_to_json_file([{
            "loc": location['country'],
            "url": link_object['url'],
            "num_occurrences": link_object['num_occurrences']
        } for link_object in link_objects], f"{self.res_dir}/crawled_links.json")
        return link_objects

    def quit(self) -> Any:
        self.driver.quit()
