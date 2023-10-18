import os
import time

import requests
from seleniumrequests import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webelement import WebElement
import pyotp

from adapter_base import AdapterBase, login_required

graph_api_version = "v16.0"
page_id = "204304653318353"


def get_long_lived_token(config: dict) -> str:
    """
    Use the short-lived graph-api access token to get a long-lived page token.
    Using https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived

    :param config: All the secrets
    :return: Long-lived page token
    """
    api_response = requests.get(f"https://graph.facebook.com/{graph_api_version}/oauth/access_token",
                                {"grant_type": "fb_exchange_token",
                                 "client_id": config['FACEBOOK_APP_ID'],
                                 "client_secret": config['FACEBOOK_APP_SECRET'],
                                 "fb_exchange_token": config['FACEBOOK_GRAPH_API_TOKEN']}).json()
    long_lived_token = api_response['access_token']
    api_response = requests.get(f"https://graph.facebook.com/{graph_api_version}/me?fields=id",
                                {"access_token": config['FACEBOOK_GRAPH_API_TOKEN']}).json()
    app_scoped_user_id = api_response['id']
    api_response = requests.get(f"https://graph.facebook.com/{graph_api_version}/{app_scoped_user_id}/accounts",
                                {"access_token": long_lived_token}).json()
    pages = api_response['data']
    page_token = ''
    for page in pages:
        if page['name'] == 'DSDA Blue Suede Shoes':
            page_token = page['access_token']
    print("Long-lived token (vanilla):", long_lived_token)
    print("Long-lived page token:", long_lived_token)
    return page_token


class FacebookAdapter(AdapterBase):
    def __init__(self, driver: Firefox, username: str, password: str, totp: str, graph_api_token: str):
        super().__init__(driver, "Facebook")
        self.__username = username
        self.__password = password
        self.__totp = totp
        self.__graph_api_token = graph_api_token

    def login(self):
        if self.logged_in:
            return
        self.driver.get("https://www.facebook.com/")
        essential_cookies_button = self.driver.find_element(By.XPATH, '//button[@title="Decline optional cookies"]')
        login_button = self.driver.find_element(By.XPATH, '//button[@name="login"]')
        email_field = self.driver.find_element(By.ID, "email")
        password_field = self.driver.find_element(By.ID, "pass")

        essential_cookies_button.click()
        time.sleep(0.3)
        email_field.send_keys(self.__username)
        password_field.send_keys(self.__password)
        login_button.click()

        WebDriverWait(self.driver, 15).until(
            expected_conditions.presence_of_element_located(
                (By.ID, 'approvals_code'),
            )
        )
        code_field = self.driver.find_element(By.ID, "approvals_code")
        code_submit_button = self.driver.find_element(By.ID, "checkpointSubmitButton")
        totp = pyotp.TOTP(self.__totp)
        code_field.send_keys(totp.now())
        code_submit_button.click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.text_to_be_present_in_element(
                (By.TAG_NAME, 'strong'),
                "Browser"
            )
        )

        remember_submit_button = self.driver.find_element(By.ID, "checkpointSubmitButton")
        remember_radio = self.driver.find_elements(By.CLASS_NAME, "uiInputLabelInput")[1]  # Don't remember
        remember_radio.click()
        remember_submit_button.click()

        try:
            WebDriverWait(self.driver, 15).until(expected_conditions.url_to_be("https://www.facebook.com/"))
        except TimeoutException:
            print("Timeout for automatic continuation")
            input("Press enter to continue manually")

        # Do profile switch, this goes faster on a simple page like this for some reason.
        self.driver.get("https://www.facebook.com/events/create/")

        # Click profile picture
        profile_svg = self.driver.find_element(By.XPATH, '//*[name()="svg" and @aria-label="Je profiel"]')
        profile_svg.click()
        # Click switch profile
        profile_switch = self.driver.find_element(By.XPATH, '//div[@aria-label="Van profiel wisselen"]')
        profile_switch.click()

        time.sleep(0.5)
        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_to_be("https://www.facebook.com/events/create/")
        )

        self.logged_in = True

    def get_events(self):
        """
        List events present on the Facebook page

        :return: List of events
        """
        api_response = requests.get(f"https://graph.facebook.com/{graph_api_version}/{page_id}/events",
                                    {"access_token": self.__graph_api_token})
        # Todo: get long lived token
        # https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived
        if api_response.status_code == 400:
            raise Exception(f"Facebook Graph API error: {api_response.json()['error']['message']}")
        return_events = api_response.json()['data']
        return return_events

    def _fil_event_info(self, event_info: dict):
        # Setting image
        filename = os.path.join(os.getcwd(), event_info['image_name'])
        file = self.driver.find_element(By.XPATH, '//input[@type="file"]')
        file.send_keys(filename)

        self.driver.implicitly_wait(0)
        end_field_test = self.driver.find_elements(By.XPATH, '//label[@aria-label="Einddatum"]//input')
        if len(end_field_test) == 0:
            # Open end date and time
            self.driver.find_element(By.XPATH, '//*[contains(text(), "Einddatum en -tijd")]').click()
        self.driver.implicitly_wait(5)

        event_name_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Evenementnaam"]//input')
        event_name_field.clear()
        event_name_field.send_keys(event_info['name'])

        # Date and time
        event_start_date_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Begindatum"]//input')
        event_start_date_field.send_keys([Keys.BACK_SPACE] * 20 + [Keys.DELETE] * 20)
        event_start_date_field.send_keys(event_info['start'].strftime("%d-%m-%Y"))

        event_start_time_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Starttijd"]//input')
        event_start_time_field.click()
        event_start_time_field.send_keys([Keys.BACK_SPACE] * 20 + [Keys.DELETE] * 20)
        event_start_time_field.send_keys(event_info['start'].strftime("%H:%M"))

        event_end_date_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Einddatum"]//input')
        event_end_date_field.click()
        event_end_date_field.send_keys([Keys.BACK_SPACE] * 20 + [Keys.DELETE] * 20)
        event_end_date_field.send_keys(event_info['end'].strftime("%d-%m-%Y"))

        event_end_time_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Eindtijd"]//input')
        event_end_time_field.click()
        event_end_time_field.send_keys([Keys.BACK_SPACE] * 20 + [Keys.DELETE] * 20)
        event_end_time_field.send_keys(event_info['end'].strftime("%H:%M"))

        # Click this is a personal event, not online
        self.driver.find_element(By.XPATH, '//label[@aria-label="Is dit persoonlijk of virtueel?"]').click()
        self.driver.find_element(By.XPATH, '//div[@role="option"][1]').click()  # First option

        # Location
        location_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Locatie toevoegen"]//input')
        location_field.clear()
        location_field.send_keys(f"{event_info['venue']}, {event_info['address']}")

        event_name_field.click()  # Make other fields visible again
        # Event details (description)
        details_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Wat zijn de details?"]//textarea')
        details_field.click()
        details_field.clear()
        details_field.send_keys(event_info['content-unicode'])

    @login_required
    def update_event(self, event_info: dict, existing_event: dict):
        edit_url = f"https://www.facebook.com/events/edit/{existing_event['id']}"
        self.driver.get(edit_url)
        time.sleep(0.5)

        self._fil_event_info(event_info)

        # Hit update
        self.driver.find_element(By.XPATH, '//div[@aria-label="Opslaan"]').click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_contains(f"https://www.facebook.com/events/{existing_event['id']}")
        )

        long_url, short_url = self.get_event_urls()
        print(f"Facebook: Edited event at {long_url}")
        print(f"          Short URL is {short_url}")
        return long_url, short_url

    @login_required
    def create_event(self, event_info: dict):
        self.driver.get("https://www.facebook.com/events/create/")
        time.sleep(0.5)

        self._fil_event_info(event_info)

        # Hit create event
        self.driver.find_element(By.XPATH, '//div[@aria-label="Evenement maken"]').click()

        WebDriverWait(self.driver, 20).until(
            expected_conditions.url_changes("https://www.facebook.com/events/create/")
        )
        time.sleep(1)

        long_url, short_url = self.get_event_urls()
        print(f"Facebook: Created new event at {long_url}")
        print(f"          Short URL is {short_url}")
        return long_url, short_url

    @login_required
    def get_event_urls(self) -> tuple[str, str]:
        long_url = self.driver.current_url.split('?')[0]
        # self.driver.find_element(By.XPATH, '//div[@aria-label="Delen"]').click()
        # time.sleep(0.1)
        short_url = ""  # self.driver.find_element(By.XPATH, '//span[contains(text(), "fb.me")]').text
        return long_url, short_url
