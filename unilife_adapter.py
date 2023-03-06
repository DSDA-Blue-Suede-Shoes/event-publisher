from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime
from utils import DEFAULT_TZ


class UnilifeAdapter:
    def __init__(self, driver: WebDriver, username, password):
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

        self.driver.get('https://app.uni-life.nl/event')

        WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.XPATH, "//tbody/tr//span"))
        )

        rows = self.driver.find_elements(By.XPATH, "//tbody/tr")
        events = []
        for row in rows:
            name = row.find_element(By.XPATH, "td[@data-label='Title']").text
            full_text = row.text
            link = row.find_element(By.XPATH, "td[@data-label='Actions']//li[1]/a").get_property('href')
            events.append({'name': name, 'full_text': full_text, 'link': link})
        pass
        return events

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
