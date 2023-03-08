from seleniumrequests import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.action_chains import ActionChains
import requests
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

        self.driver.get('https://app.uni-life.nl/event/create')

        WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.XPATH, "//input[@name='name']"))
        )

        self.driver.find_element(By.XPATH, "//input[@name='name']").send_keys(event['name'])
        self.driver.find_element(By.XPATH, "//textarea[@name='description']").send_keys(event['content'])
        self.driver.find_element(By.XPATH, "//vue-autocomplete[1]//button").click()  # Select all universities
        self.driver.find_element(By.XPATH, "//input[@name='url']").send_keys(event['link'])
        self.driver.find_element(By.XPATH, "//input[@name='location_name']").send_keys(event['venue'])
        self.driver.find_element(By.XPATH, "//input[@name='location']").send_keys(event['venue'])
        self.driver.find_element(By.CLASS_NAME, "pac-target-input").send_keys(event['address'])
        self.driver.find_element(By.XPATH, "//input[@name='startdate']").send_keys(event['start_date'])  # fixme, Not working
        self.driver.find_element(By.XPATH, "//input[@name='enddate']").send_keys(event['end_date'])  # fixme, Not working
        self.driver.find_element(By.XPATH, "//input[@name='starttime[hours]']").send_keys(event['start'].hour)
        self.driver.find_element(By.XPATH, "//input[@name='starttime[minutes]']").send_keys(event['start'].minute)
        self.driver.find_element(By.XPATH, "//input[@name='endtime[hours]']").send_keys(event['end'].hour)
        self.driver.find_element(By.XPATH, "//input[@name='endtime[minutes]']").send_keys(event['end'].minute)
        interests_input = self.driver.find_element(By.XPATH, "//vue-autocomplete[2]//input")
        interests_input.click()
        interests_input.send_keys("dance")
        self.driver.find_element(By.XPATH, "//vue-autocomplete[2]//input[@type='checkbox']").click()
        interests_input.click()
        interests_input.send_keys("party")
        self.driver.find_element(By.XPATH, "//vue-autocomplete[2]//input[@type='checkbox']").click()
        link_text_field = self.driver.find_element(By.XPATH, "//label[8]/vue-autocomplete")
        link_text_field.click()
        link_text_field.find_element(By.XPATH, "//div[@class='results']/ul/li[1]").click()

        pass

    def update_event(self, unilife_event_ob, event):
        pass
