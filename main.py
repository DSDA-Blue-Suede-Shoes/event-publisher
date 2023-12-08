import warnings
import sys
import html
import os
from json import loads

import requests
from datetime import datetime

from seleniumrequests import Firefox
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup

from calendar_adapter import CalendarAdapter
from facebook_adapter import FacebookAdapter, get_long_lived_token
from text_transforms import trim_list, get_list, render_unicode, render_whatsapp
from unilife_adapter import UnilifeAdapter
from utils import DEFAULT_TZ, ask_confirmation

headers = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}


def get_events():
    print("Getting events from website")
    events_raw = requests.get("https://dsda.nl/wp-json/wp/v2/tribe_events?per_page=25", headers=headers).json()
    events = [{'name': html.unescape(event['title']['rendered']), 'content': event['content']['rendered'],
               'link': event['link'], 'slug': event['slug']} for event in events_raw]

    return events


def get_event_info(event: dict) -> dict:
    event_page = requests.get(event['link'], headers=headers)
    soup = BeautifulSoup(event_page.text, 'html.parser')

    start_date = soup.find("abbr", "tribe-events-start-date")['title']
    end_date = soup.find("div", "tribe-events-start-time")['title']
    times = soup.find("div", "tribe-events-start-time").text.strip()
    times = times.split(' - ')
    event['start_date'] = start_date
    event['end_date'] = end_date
    event['start_time'] = times[0]
    event['end_time'] = times[1]
    event['start'] = DEFAULT_TZ.localize(
        datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M"))
    event['end'] = DEFAULT_TZ.localize(datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M"))

    try:
        event['venue'] = soup.find("dd", "tribe-venue").text.strip()
    except AttributeError:
        event['venue'] = ''

    if soup.find("span", "tribe-street-address") is not None:
        try:
            address = soup.find("span", "tribe-street-address").text.strip()
        except AttributeError:
            address = ''
        try:
            postal_code = soup.find("span", "tribe-postal-code").text.strip()
        except AttributeError:
            postal_code = ''
        try:
            locality = soup.find("span", "tribe-locality").text.strip()
        except AttributeError:
            locality = ''
        event['address'] = f'{address}, {postal_code} {locality}'
    else:
        event['address'] = ''

    categories_wrapper = soup.find("dd", "tribe-events-event-categories")
    categories = [cat.text for cat in categories_wrapper.find_all('a')]
    event['categories'] = categories

    content_soup = BeautifulSoup(event['content'], 'html.parser')
    content_text_list = trim_list(get_list(content_soup.children))
    event['content-unicode'] = render_unicode(content_text_list)
    event['content-whatsapp'] = render_whatsapp(content_text_list) + f"\n\nAll details:\n{event['link']}"

    image_url = soup.find("img", "wp-post-image")['src']
    r = requests.get(image_url, stream=True, headers=headers)
    if r.status_code == 200:
        extension = image_url.split(".")[-1].lower()
        event['image_name'] = f'event-image.{extension}'
        with open(event['image_name'], 'wb') as f:
            import shutil
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
    else:
        warnings.warn("Could not download event image.")

    return event


def create_driver():
    if os.name == 'posix':
        ff_path = 'geckodriver'  # Same Directory as Python Program
    else:
        ff_path = 'geckodriver.exe'  # Same Directory as Python Program
    service = Service(executable_path=ff_path)

    options = Options()
    #options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

    driver = Firefox(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def get_config() -> dict:
    """
    Get the authentication data from either the credentials.json file, or environment variables.

    :return: Authentication config
    """
    try:
        with open("credentials.json", "r", encoding="utf-8") as f:
            conf = loads(f.read())
    except FileNotFoundError as error:
        print("Could not find credentials.json")

    conf["FACEBOOK_ID"] = os.getenv("FACEBOOK_ID", conf.get("FACEBOOK_ID"))
    conf["FACEBOOK_PASSWORD"] = os.getenv("FACEBOOK_PASSWORD", conf.get("FACEBOOK_PASSWORD"))
    conf["FACEBOOK_TOTP"] = os.getenv("FACEBOOK_TOTP", conf.get("FACEBOOK_TOTP"))
    conf["FACEBOOK_GRAPH_API_TOKEN"] = os.getenv("FACEBOOK_GRAPH_API_TOKEN", conf.get("FACEBOOK_GRAPH_API_TOKEN"))
    conf["FACEBOOK_APP_ID"] = os.getenv("FACEBOOK_APP_ID", conf.get("FACEBOOK_APP_ID"))
    conf["FACEBOOK_APP_SECRET"] = os.getenv("FACEBOOK_APP_SECRET", conf.get("FACEBOOK_APP_SECRET"))
    conf["UNILIFE_ID"] = os.getenv("UNILIFE_ID", conf.get("UNILIFE_ID"))
    conf["UNILIFE_PASSWORD"] = os.getenv("UNILIFE_PASSWORD", conf.get("UNILIFE_PASSWORD"))

    assert conf["FACEBOOK_ID"] is not None
    assert conf["FACEBOOK_PASSWORD"] is not None
    assert conf["FACEBOOK_TOTP"] is not None
    assert conf["FACEBOOK_GRAPH_API_TOKEN"] is not None
    assert conf["UNILIFE_ID"] is not None
    assert conf["UNILIFE_PASSWORD"] is not None

    return conf


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    config = get_config()

    print("Event publisher, at your service")

    # get_long_lived_token(config)  # Use when you need such a token. Obviously.

    calendar = CalendarAdapter()
    driver = None
    unilife_adapter = None
    facebook_adapter = None

    quit_loop = False
    while not quit_loop:
        events = get_events()
        continue_loop = False
        # Interfacing with user
        # Select event or quit
        print("\nSelect event to process:")
        print("  Press q to quit, r to refresh")
        for i, event in enumerate(events):
            print(f"  {i + 1}: {event['name']}")
            pass

        choice = -1
        while choice <= 0 or choice > len(events):
            _input = input("Pick: ")
            if _input == 'q':
                quit_loop = True
                break
            if _input == 'r':
                continue_loop = True
                break
            choice = int(_input)

        if quit_loop:
            print("Quitting")
            break

        if continue_loop:
            continue

        # Actual work with the event
        event = events[choice - 1]
        event = get_event_info(event)

        print(f"Processing {event['name']} on {event['start_date']}")

        if ask_confirmation("Do you want to put this in the Google Calendar?"):
            g_events = calendar.do_event(event)

        if ask_confirmation("Do you want to put this event on Unilife?"):
            if driver is None:
                driver = create_driver()
            if unilife_adapter is None:
                unilife_adapter = UnilifeAdapter(driver, config["UNILIFE_ID"], config["UNILIFE_PASSWORD"])
            unilife_success = unilife_adapter.do_event(event)

        if ask_confirmation("Do you want to put this event on Facebook?"):
            if driver is None:
                driver = create_driver()
            if facebook_adapter is None:
                facebook_adapter = FacebookAdapter(driver, config["FACEBOOK_ID"], config["FACEBOOK_PASSWORD"],
                                                   config["FACEBOOK_TOTP"], config["FACEBOOK_GRAPH_API_TOKEN"])
            facebook_adapter.do_event(event)

        if ask_confirmation("Do you want a WhatsApp share message?"):
            print()  # New line
            print(event['content-whatsapp'])

    if driver is not None:
        driver.quit()
