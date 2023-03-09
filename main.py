import warnings

from seleniumrequests import Firefox
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
from facebook_adapter import FacebookAdapter
from text_transforms import trim_list, get_list, render_unicode, render_whatsapp
from unilife_adapter import UnilifeAdapter
from utils import DEFAULT_TZ


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

    PATH = 'C:\\Program Files\\Python311\\Scripts\\geckodriver.exe'  # Same Directory as Python Program
    options = Options()
    options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

    service = Service(executable_path=PATH)
    driver = Firefox(service=service, options=options)

    unilife_adapter = UnilifeAdapter(driver, UNILIFE_ID, UNILIFE_PASSWORD)
    unilife_adapter.login()
    unilife_success = unilife_adapter.do_event(event)

    facebook_adapter = FacebookAdapter(driver, FACEBOOK_ID, FACEBOOK_PASSWORD, FACEBOOK_TOTP)
    facebook_adapter.login()
    facebook_adapter.create_event(event)
