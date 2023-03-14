import warnings
import sys
import html
import os
import requests
from datetime import datetime

from seleniumrequests import Firefox
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup

from calendar_adapter import CalendarAdapter
from facebook_adapter import FacebookAdapter
from text_transforms import trim_list, get_list, render_unicode, render_whatsapp
from unilife_adapter import UnilifeAdapter
from utils import DEFAULT_TZ, ask_confirmation


def get_events():
    print("Getting events from website")
    events_raw = requests.get("https://dsda.nl/wp-json/wp/v2/tribe_events").json()
    events = [{'name': html.unescape(event['title']['rendered']), 'content': event['content']['rendered'],
               'link': event['link'], 'slug': event['slug']} for event in events_raw]

    return events


def get_event_info(event: dict) -> dict:
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
    event['start'] = DEFAULT_TZ.localize(
        datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M"))
    event['end'] = DEFAULT_TZ.localize(datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M"))
    event['venue'] = soup.find("dd", "tribe-venue").text.strip()
    # Fixme, not all these are always defined
    event['address'] = f'{soup.find("span", "tribe-street-address").text.strip()}, {soup.find("span", "tribe-postal-code").text.strip()} {soup.find("span", "tribe-locality").text.strip()}'

    categories_wrapper = soup.find("dd", "tribe-events-event-categories")
    categories = [cat.text for cat in categories_wrapper.find_all('a')]
    event['categories'] = categories

    content_soup = BeautifulSoup(event['content'], 'html.parser')
    content_text_list = trim_list(get_list(content_soup.children))
    event['content-unicode'] = render_unicode(content_text_list)
    event['content-whatsapp'] = render_whatsapp(content_text_list)

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


def create_driver():
    ff_path = 'C:\\Program Files\\Python311\\Scripts\\geckodriver.exe'  # Same Directory as Python Program
    service = Service(executable_path=ff_path)

    options = Options()
    options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

    return Firefox(service=service, options=options)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    FACEBOOK_ID = os.getenv("FACEBOOK_ID")
    FACEBOOK_PASSWORD = os.getenv("FACEBOOK_PASSWORD")
    FACEBOOK_TOTP = os.getenv("FACEBOOK_TOTP")
    FACEBOOK_GRAPH_API_TOKEN = os.getenv("FACEBOOK_GRAPH_API_TOKEN")
    UNILIFE_ID = os.getenv("UNILIFE_ID")
    UNILIFE_PASSWORD = os.getenv("UNILIFE_PASSWORD")

    assert FACEBOOK_ID is not None
    assert FACEBOOK_PASSWORD is not None
    assert FACEBOOK_TOTP is not None
    assert FACEBOOK_GRAPH_API_TOKEN is not None
    assert UNILIFE_ID is not None
    assert UNILIFE_PASSWORD is not None

    print("Event publisher, at your service")

    events = get_events()

    calendar = CalendarAdapter()
    driver = None
    unilife_adapter = None
    facebook_adapter = None

    quit_loop = False
    while not quit_loop:
        # Interfacing with user
        # Select event or quit
        print("\nSelect event to process:")
        print("  Press q to quit")
        for i, event in enumerate(events):
            print(f"  {i + 1}: {event['name']}")
            pass

        choice = -1
        while choice <= 0 or choice > len(events):
            _input = input("Pick: ")
            if _input == 'q':
                quit_loop = True
                break
            choice = int(_input)

        if quit_loop:
            print("Quitting")
            break

        # Actual work with the event
        event = events[choice - 1]
        event = get_event_info(event)

        if ask_confirmation("Do you want to put this in the Google Calendar?"):
            g_events = calendar.do_event(event)

        if ask_confirmation("Do you want to put this event on Unilife?"):
            if driver is None:
                driver = create_driver()
            if unilife_adapter is None:
                unilife_adapter = UnilifeAdapter(driver, UNILIFE_ID, UNILIFE_PASSWORD)
            unilife_success = unilife_adapter.do_event(event)

        if ask_confirmation("Do you want to put this event on Facebook?"):
            if driver is None:
                driver = create_driver()
            if facebook_adapter is None:
                facebook_adapter = FacebookAdapter(driver, FACEBOOK_ID, FACEBOOK_PASSWORD,
                                                   FACEBOOK_TOTP, FACEBOOK_GRAPH_API_TOKEN)
            facebook_adapter.do_event(event)

    if driver is not None:
        driver.quit()
