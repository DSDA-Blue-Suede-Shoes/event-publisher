import os
import time

from seleniumrequests import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webelement import WebElement
import pyotp


class FacebookAdapter:
    def __init__(self, driver: Firefox, username, password, totp):
        self.driver = driver
        self.logged_in = False
        self.__username = username
        self.__password = password
        self.__totp = totp

    def login(self):
        if self.logged_in:
            return
        self.driver.get("https://www.facebook.com/")
        essential_cookies_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "Only allow essential cookies")]')
        login_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "Login")]')
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

        self.logged_in = True

    def create_event(self, event_info: dict):
        self.driver.get("https://www.facebook.com/events/create/")
        pass
        profile_svg = self.driver.find_element(By.XPATH, '//*[name()="svg" and @aria-label="Je profiel"]')
        profile_svg.click()
        profile_switch = self.driver.find_element(By.XPATH, '//div[@aria-label="Van profiel wisselen"]')
        profile_switch.click()

        time.sleep(2)
        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_to_be("https://www.facebook.com/events/create/")
        )
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

        long_url = self.driver.current_url
        print(f"Facebook: Created new event at {long_url}")
        self.driver.find_element(By.XPATH, '//div[@aria-label="Delen"]').click()
        short_url = self.driver.find_element(By.XPATH, '//span[contains(text(), "fb.me")]').text
        print(f"          Short URL is {short_url}")

        return long_url, short_url
