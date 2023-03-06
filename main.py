import warnings

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import requests
from bs4 import BeautifulSoup
import time
import os
import pyotp
from datetime import datetime
from calendar_adapter import CalendarAdapter
from unilife_adapter import UnilifeAdapter
from utils import DEFAULT_TZ


def facebook_login(id: str, password: str):
    buttons = driver.find_elements(By.TAG_NAME, "button")
    essential_cookies_button = first = next(filter(lambda button: button.text == 'Only allow essential cookies', buttons), None)
    login_button = first = next(filter(lambda button: button.text == 'Log in', buttons), None)
    email_field = driver.find_element(By.ID, "email")
    password_field = driver.find_element(By.ID, "pass")

    essential_cookies_button.click()
    email_field.send_keys(id)
    password_field.send_keys(password)
    login_button.click()

    WebDriverWait(driver, 10).until(
        expected_conditions.presence_of_element_located(
            (By.ID, 'approvals_code'),
        )
    )
    code_field = driver.find_element(By.ID, "approvals_code")
    code_submit_button = driver.find_element(By.ID, "checkpointSubmitButton")
    totp = pyotp.TOTP(FACEBOOK_TOTP)
    code_field.send_keys(totp.now())
    code_submit_button.click()

    WebDriverWait(driver, 10).until(
        expected_conditions.text_to_be_present_in_element(
            (By.TAG_NAME, 'strong'),
            "Browser"
        )
    )

    remember_submit_button = driver.find_element(By.ID, "checkpointSubmitButton")
    remember_radio = driver.find_elements(By.CLASS_NAME, "uiInputLabelInput")[1]  # Don't remember
    remember_radio.click()
    remember_submit_button.click()

    from selenium.common import TimeoutException
    try:
        WebDriverWait(driver, 10).until(expected_conditions.url_to_be("https://www.facebook.com/"))
    except TimeoutException:
        print("Timeout for automatic continuation")
        input("Press enter to continue manually")


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


def find_element_by_attribute(by: By, el_search: str, attribute: str, match_list: list):
    """
    Finds the first element that has an attribute value matching to something in match_list.

    :param by: What to initially search by
    :param el_search: Element search string
    :param attribute: Attribute name
    :param match_list: Attribute match strings
    :return:
    """
    els = driver.find_elements(by, el_search)
    return next(filter(lambda el: attribute_match(el, attribute, match_list), els), None)


def facebook_event(event_info):
    driver.get("https://www.facebook.com/events/create/")
    pass
    profile_svg = find_element_by_attribute(By.TAG_NAME, "svg", "aria-label", ["Je profiel", "Your profile"])
    profile_svg.click()
    profile_switch = find_element_by_attribute(By.TAG_NAME, "div", "aria-label", ["profiel wisselen", "witch profile"])
    profile_switch.click()

    time.sleep(2)
    WebDriverWait(driver, 10).until(
        expected_conditions.url_to_be("https://www.facebook.com/events/create/")
    )

    driver.get("https://www.facebook.com/events/create/")
    omslagfoto = find_element_by_attribute(By.TAG_NAME, "div", "aria-label", ["Omslagfoto toevoegen"])
    filename = r"K:\Pictures\Ontwerpen\DSDA\Banner\Tango Café"
    file = find_element_by_attribute(By.TAG_NAME, "input", "type", ["file"])
    file.send_keys(filename)
    omslagfoto.click()
    actions = ActionChains(driver)
    actions.send_keys(Keys.TAB)
    actions.send_keys(Keys.ENTER)
    actions.perform()
    pass


def get_events():
    events_raw = requests.get("https://dsda.nl/wp-json/wp/v2/tribe_events").json()
    events = [{'name': event['title']['rendered'], 'content': event['content']['rendered'],
               'link': event['link'], 'slug': event['slug']} for event in events_raw]
    print("Select event:")
    for i, event in enumerate(events):
        print(f"  {i+1}: {event['name']}")

    choice = -1
    while choice <= 0 or choice > len(events):
        choice = int(input("Pick"))
    event = events[choice-1]

    event_page = requests.get(event['link'])
    soup = BeautifulSoup(event_page.text, 'html.parser')

    start_date = soup.find("abbr", "tribe-events-start-date")['title']
    end_date = soup.find("div", "tribe-events-start-time")['title']
    times = soup.find("div", "tribe-events-start-time").text.strip()
    times = times.split(' - ')
    event['start_date'] = start_date
    event['end_date'] = end_date
    event['start_time'] = times[0]
    event['end_time'] = times[1]
    event['start'] = DEFAULT_TZ.localize(datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M"))
    event['end'] = DEFAULT_TZ.localize(datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M"))
    event['venue'] = soup.find("dd", "tribe-venue").text.strip()
    event['address'] = f'{soup.find("span", "tribe-street-address").text.strip()}, {soup.find("span", "tribe-postal-code").text.strip()} {soup.find("span", "tribe-locality").text.strip()}'

    # content = soup.find("div", "tribe-events-content").text.strip()
    # event['content'] = content

    categories_wrapper = soup.find("dd", "tribe-events-event-categories")
    categories = [cat.text for cat in categories_wrapper.find_all('a')]
    event['categories'] = categories

    image_url = soup.find("img", "wp-post-image")['src']
    r = requests.get(image_url, stream=True)
    if r.status_code == 200:
        with open('event-image.jpg', 'wb') as f:
            import shutil
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
    else:
        warnings.warn("Could not download event image.")

    return event


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    FACEBOOK_ID = os.getenv("FACEBOOK_ID")
    FACEBOOK_PASSWORD = os.getenv("FACEBOOK_PASSWORD")
    FACEBOOK_TOTP = os.getenv("FACEBOOK_TOTP")
    assert FACEBOOK_ID is not None
    assert FACEBOOK_PASSWORD is not None

    UNILIFE_ID = os.getenv("UNILIFE_ID")
    UNILIFE_PASSWORD = os.getenv("UNILIFE_PASSWORD")

    event = get_events()

    calendar = CalendarAdapter()
    g_events = calendar.do_event(event)
    # g_event = calendar.find_event(event)
    # calendar.create_event(event)

    PATH = 'C:\\Program Files\\Python311\\Scripts\\geckodriver.exe'  # Same Directory as Python Program
    options = Options()
    options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

    service = Service(executable_path=PATH)
    driver = webdriver.Firefox(service=service, options=options)

    unilife_adapter = UnilifeAdapter(driver, UNILIFE_ID, UNILIFE_PASSWORD)
    unilife_adapter.login()
    unilife_events = unilife_adapter.get_events()
    if unilife_events:
        print("Select event to edit (0 to create new):")
        for i, event_ob in enumerate(unilife_events):
            print(f"  {i + 1}: {event_ob['name']}")

        choice = int(input("Pick"))
        if 0 < choice <= len(unilife_events):
            event_ob = unilife_events[choice]
            print(f"Choose {event_ob['name']}")
            unilife_adapter.update_event(event_ob, event)
        else:
            unilife_adapter.create_event(event)
    else:
        unilife_adapter.create_event(event)

    driver.get("https://www.facebook.com/")
    # time.sleep(1)
    facebook_login(FACEBOOK_ID, FACEBOOK_PASSWORD)
    facebook_event(event)
