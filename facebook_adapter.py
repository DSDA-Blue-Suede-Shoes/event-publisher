import time

from seleniumrequests import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webelement import WebElement
import pyotp
import base64
from bs4 import BeautifulSoup
from typing import BinaryIO


def attribute_match(el: WebElement, attribute: str, match_list: list):
    """
    Checks if a given element has an attribute value matching to something in match_list.

    :param el: Element to check
    :param attribute: Attribute name
    :param match_list: Attribute match strings
    :return: Whether attribute has matching value
    """
    aria_attribute = el.get_attribute(attribute)
    if aria_attribute is None:
        return False
    for match in match_list:
        if match in aria_attribute:
            return True
    return False


def find_element_by_attribute(driver: Firefox, by: By, el_search: str, attribute: str, match_list: list):
    """
    Finds the first element that has an attribute value matching to something in match_list.

    :param driver: Selenium driver
    :param by: What to initially search by
    :param el_search: Element search string
    :param attribute: Attribute name
    :param match_list: Attribute match strings
    :return:
    """
    els = driver.find_elements(by, el_search)
    return next(filter(lambda el: attribute_match(el, attribute, match_list), els), None)


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
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        essential_cookies_button = first = next(
            filter(lambda button: button.text == 'Only allow essential cookies', buttons), None)
        login_button = first = next(filter(lambda button: button.text == 'Log in', buttons), None)
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
        profile_svg = find_element_by_attribute(self.driver, By.TAG_NAME, "svg", "aria-label", ["Je profiel", "Your profile"])
        profile_svg.click()
        profile_switch = find_element_by_attribute(self.driver, By.TAG_NAME, "div", "aria-label",
                                                   ["profiel wisselen", "witch profile"])
        profile_switch.click()

        time.sleep(2)
        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_to_be("https://www.facebook.com/events/create/")
        )

        self.driver.get("https://www.facebook.com/events/create/")
        omslagfoto = find_element_by_attribute(self.driver, By.TAG_NAME, "div", "aria-label", ["Omslagfoto toevoegen"])
        filename = r"K:\Pictures\Ontwerpen\DSDA\Banner\Tango Café"
        file = find_element_by_attribute(self.driver, By.TAG_NAME, "input", "type", ["file"])
        file.send_keys(filename)
        omslagfoto.click()
        actions = ActionChains(self.driver)
        actions.send_keys(Keys.TAB)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        pass
