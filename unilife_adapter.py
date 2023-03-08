from seleniumrequests import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.action_chains import ActionChains
import requests
import base64
from bs4 import BeautifulSoup
from datetime import datetime
from utils import DEFAULT_TZ


class UnilifeAdapter:
    def __init__(self, driver: Firefox, username, password):
        self.driver = driver
        self.logged_in = False
        self.__username = username
        self.__password = password

    def login(self):
        if self.logged_in:
            return
        self.driver.get('https://app.uni-life.nl/login')
        username_field = self.driver.find_element(By.XPATH, "//input[@name='email']")
        password_field = self.driver.find_element(By.XPATH, "//input[@name='password']")
        login_button = self.driver.find_element(By.CLASS_NAME, 'login-btn')  # or By.XPATH, "//form[@class='login']/button"
        username_field.send_keys(self.__username)
        password_field.send_keys(self.__password)
        login_button.click()
        WebDriverWait(self.driver, 10).until(
            expected_conditions.url_to_be("https://app.uni-life.nl/event")
        )
        self.logged_in = True

    def get_events(self):
        if not self.logged_in:
            self.login()

        r = self.driver.request('GET', "https://app.uni-life.nl/event",
                                params={'direction': 'asc', 'search': '', 'filter': '', 'page': 0},
                                headers={"Accept": "application/json, text/plain, */*"})
        unilife_events = r.json()['body']
        return_events = []

        for event in unilife_events:
            return_events.append({
                'name': event['content'][0]['value'],
                'location': event['content'][3]['value'],
                'start_date': event['content'][4]['value'],
                'end_date': event['content'][5]['value'],
                'link': event['metadata']['actions'][0]['url'],
            })
        return return_events

    def create_event(self, event: dict):
        if not self.logged_in:
            self.login()

        # Get a creation token. Not sure if and why this is necessary.
        r = self.driver.request('GET', "https://app.uni-life.nl/event/create")
        soup = BeautifulSoup(r.text, 'html.parser')
        token_input = soup.find("input", {'name': '_token'})
        token = token_input.get('value')

        # Create form data
        with open("event-image.jpg", "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())

        values = {
            "_token":               token,
            "name":                 event['name'],
            "description":          event['content'],
            "event_type_id":        1,
            "association":          331,
            "universities[]":       8,
            "interests[]":          [64, 44],
            "url":                  event['link'],
            "button_text":          1,
            "location_name":        event['venue'],
            "location":             event['venue'],
            "location_address":     event['address'],
            'eventimage[img_source]':           encoded_string,
            "eventimage[img_discover_big]":     '{"width":1158,"height":1006,"left":181,"top":0}',
            "eventimage[img_discover_small]":   '{"width":1835,"height":1006,"left":42,"top":0}',
            "eventimage[img_card]":             '{"width":1635,"height":1006,"left":79,"top":0}',
            "eventimage[img_details]":          '{"width":1424,"height":1006,"left":92,"top":0}',
            "startdate":            event['start'].strftime("%d-%m-%Y"),
            "starttime[hours]":     event['start'].hour,
            "starttime[minutes]":   event['start'].minute,
            "enddate":              event['end'].strftime("%d-%m-%Y"),
            "endtime[hours]":       event['end'].hour,
            "endtime[minutes]":     event['end'].minute,
            "visibility":           "public"
        }
        # Post event
        posted = self.driver.request('POST', "https://app.uni-life.nl/event/create", data=values)
        return posted.status_code == 200

    def update_event(self, unilife_event_ob, event):
        pass
