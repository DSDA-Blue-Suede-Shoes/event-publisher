import warnings

from seleniumrequests import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
import base64
from bs4 import BeautifulSoup
from typing import BinaryIO

from adapter_base import AdapterBase, login_required


class UnilifeAdapter(AdapterBase):
    def __init__(self, driver: Firefox, username: str, password: str):
        super().__init__(driver, "Unilife")
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

    @login_required
    def get_events(self):
        """
        List events present in our Unilife account

        :return: List of events
        """
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

    @staticmethod
    def unilife_event_from_event(event: dict, token: str, image: BinaryIO | None) -> dict:
        """
        Create a dictionary in Unilife format from event info.

        :param event: Source event info
        :param token: Form token
        :param image: Image file
        :return: Event info in Calendar format
        """

        values = {
            "_token": token,
            "name": event['name'],
            "description": event['content-unicode'],
            "event_type_id": 1,
            "association": 331,
            "universities[]": 8,
            "interests[]": [64, 44],
            "url": event['link'],
            "button_text": 1,
            "location_name": event['venue'],
            "location": event['venue'],
            "location_address": event['address'],
            "startdate": event['start'].strftime("%d-%m-%Y"),
            "starttime[hours]": event['start'].hour,
            "starttime[minutes]": event['start'].minute,
            "enddate": event['end'].strftime("%d-%m-%Y"),
            "endtime[hours]": event['end'].hour,
            "endtime[minutes]": event['end'].minute,
            "visibility": "public"
        }

        # If an image is supplied, include it and sizing information
        if image:
            encoded_string = base64.b64encode(image.read())
            image.close()
            update = {
                'eventimage[img_source]': encoded_string,
                "eventimage[img_discover_big]": '{"width": 1158, "height": 1006, "left": 181, "top": 0}',
                "eventimage[img_discover_small]": '{"width": 1835, "height": 1006, "left": 42, "top": 0}',
                "eventimage[img_card]": '{"width": 1635, "height": 1006, "left": 79, "top": 0}',
                "eventimage[img_details]": '{"width": 1424, "height": 1006, "left": 92, "top": 0}',
            }
            values.update(update)

        return values

    def create_event(self, event: dict):
        """
        Create Unilife event based on the supplied event information.

        :param event: Source info
        :return: If creation was successful
        """
        created_event = self.general_event_action(event, "https://app.uni-life.nl/event/create")
        if created_event:
            print(f"Unilife: Created {event['name']} event")
        else:
            warnings.warn(f"Unilife: Something went wrong creating the {event['name']} event")
        return created_event

    def update_event(self, event: dict, unilife_event: dict, ):
        """
        Update Unilife event based on the supplied event information.

        :param event: Source info
        :param unilife_event: Existing Unilife event info
        :return: If update was successful
        """
        updated_event = self.general_event_action(event, unilife_event['link'], {"_method": "PUT"})
        if updated_event:
            print(f"Unilife: Updated {event['name']} event")
        else:
            warnings.warn(f"Unilife: Something went wrong updating the {event['name']} event")
        return updated_event

    def general_event_action(self, event: dict, url: str, value_additions: dict | None = None):
        """
        Functional part of updating/creating a Unilife event.

        :param event: Event source info
        :param url: URL to use for posting info to. Can result in create or update.
        :param value_additions: For updates, the _method property should be PUT, this is used to pass that info.
        :return: If post was successful
        """
        if value_additions is None:
            value_additions = {}
        if not self.logged_in:
            self.login()

        # Get a creation token. Not sure if and why this is necessary.
        r = self.driver.request('GET', url)
        soup = BeautifulSoup(r.text, 'html.parser')
        token_input = soup.find("input", {'name': '_token'})
        token = token_input.get('value')

        # Create form data
        values = self.unilife_event_from_event(event, token, open("event-image.jpg", "rb"))
        values.update(value_additions)

        # Post event
        posted = self.driver.request('POST', url, data=values)
        return posted.status_code == 200
