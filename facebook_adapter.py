import os
import time
from typing import Tuple

import requests
from seleniumrequests import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webelement import WebElement
import pyotp

from adapter_base import AdapterBase, login_required


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
        essential_cookies_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "Only allow essential cookies")]')
        login_button = self.driver.find_element(By.XPATH, '//button[@name="login"]')
        email_field = self.driver.find_element(By.ID, "email")
        password_field = self.driver.find_element(By.ID, "pass")

        essential_cookies_button.click()
        email_field.send_keys(self.__username)
        password_field.send_keys(self.__password)
        login_button.click()

        WebDriverWait(self.driver, 10).until(
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

        from selenium.common import TimeoutException
        try:
            WebDriverWait(self.driver, 10).until(expected_conditions.url_to_be("https://www.facebook.com/"))
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
        api_response = requests.get("https://graph.facebook.com/v16.0/204304653318353/events",
                                    {"access_token": self.__graph_api_token})
        return_events = api_response.json()['data']
        return return_events

    @login_required
    def update_event(self, event_info: dict, existing_event: dict):
        edit_url = f"https://www.facebook.com/events/edit/{existing_event['id']}"
        self.driver.get(edit_url)
        time.sleep(0.5)

        event_name_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Evenementnaam"]//input')
        event_name_field.clear()
        event_name_field.send_keys(event_info['name'])

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

        event_name_field.click()  # Make other fields visible again
        details_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Beschrijving"]//textarea')
        details_field.clear()
        details_field.click()
        details_field.send_keys(event_info['content-unicode'])

        # Click category
        self.driver.find_element(By.XPATH, '//label[@aria-label="Categorie"]').click()
        # Click dance
        self.driver.find_element(By.XPATH, '//div[@role="option"]//span[contains(text(), "Dans")]').click()

        # Hit next
        self.driver.find_element(By.XPATH, '//div[@aria-label="Volgende"]').click()

        location_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Locatie"]//input')
        location_field.clear()
        location_field.send_keys(f"{event_info['venue']}, {event_info['address']}")

        # Hit next
        self.driver.find_element(By.XPATH, '//div[@aria-label="Volgende"]').click()

        # Remove image
        self.driver.find_element(By.XPATH, '//div[@aria-label="Afbeelding verwijderen"]').click()

        # Put new image
        filename = os.path.join(os.getcwd(), "event-image.jpg")
        file = self.driver.find_element(By.XPATH, '//input[@type="file"]')
        file.send_keys(filename)
        time.sleep(1)

        # Hit update
        self.driver.find_element(By.XPATH, '//div[@aria-label="Bijwerken"]').click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_changes(edit_url)
        )

        long_url, short_url = self.get_event_urls()
        print(f"Facebook: Edited event at {long_url}")
        print(f"          Short URL is {short_url}")
        return long_url, short_url

    @login_required
    def create_event(self, event_info: dict):
        self.driver.get("https://www.facebook.com/events/create/")
        time.sleep(0.5)

        filename = os.path.join(os.getcwd(), "event-image.jpg")
        file = self.driver.find_element(By.XPATH, '//input[@type="file"]')
        file.send_keys(filename)

        # Open end date and time
        self.driver.find_element(By.XPATH, '//*[contains(text(), "Einddatum en -tijd")]').click()
        event_name_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Evenementnaam"]//input')
        event_name_field.send_keys(event_info['name'])

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

        location_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Locatie toevoegen"]//input')
        location_field.send_keys(f"{event_info['venue']}, {event_info['address']}")

        event_name_field.click()  # Make other fields visible again
        details_field = self.driver.find_element(By.XPATH, '//label[@aria-label="Wat zijn de details?"]//textarea')
        details_field.click()
        details_field.send_keys(event_info['content-unicode'])

        # Hit create event
        self.driver.find_element(By.XPATH, '//div[@aria-label="Evenement maken"]').click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_changes("https://www.facebook.com/events/create/")
        )

        long_url, short_url = self.get_event_urls()
        print(f"Facebook: Created new event at {long_url}")
        print(f"          Short URL is {short_url}")
        return long_url, short_url

    @login_required
    def get_event_urls(self) -> tuple[str, str]:
        long_url = self.driver.current_url
        self.driver.find_element(By.XPATH, '//div[@aria-label="Delen"]').click()
        short_url = self.driver.find_element(By.XPATH, '//span[contains(text(), "fb.me")]').text
        return long_url, short_url
