import datetime
import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource

from utils import DEFAULT_TZ, DEFAULT_TZ_STR

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


calendar_ids = {
    'testing': 'primary',
    'general': 'q3bdd3oa0qmdk3k7plvug31u6c@group.calendar.google.com',
    # 'ballroom': 'stgo5dh75karln6v7c68b8u8d4@group.calendar.google.com',
    # 'argentine tango': '0tl34lgpbpmgncb5t400kfgsjs@group.calendar.google.com',
    # 'lindy hop': 'c_45072b8c924f957e972bc1e0aca3360eb7bb9c87802cf9b0bda9a7a69dc33cbe@group.calendar.google.com',
}


class CalendarAdapter:
    def __init__(self):
        self.service = get_service()

    @staticmethod
    def event_id(event: dict):
        return base64.b32encode(event['slug'].encode()).decode()

    def create_event(self, event: dict):
        event = {
            'id': self.event_id(event),
            'summary': event['title'],
            'location': f"{event['venue']}, {event['address']}",
            'description': event['content'],
            'start': {
                'dateTime': event['start'].isoformat(),
                'timeZone': DEFAULT_TZ_STR,
            },
            'end': {
                'dateTime': event['end'].isoformat(),
                'timeZone': DEFAULT_TZ_STR,
            },
        }

        categories = ['testing'] + list(event['categories'])

        for category in event['categories']:
            if calendar_ids.get(category) is None:
                continue
            event = self.service.events().insert(calendarId=calendar_ids[category], body=event).execute()
            print(f"Event created in {category} calendar: {event.get('htmlLink')}")

    def find_event(self, event: dict):
        id = self.event_id(event)
        try:
            event_ob = self.service.events().get(calendarId=calendar_ids['general'], eventId=id).execute()
            print("Found event using id")
            return event_ob
        except HttpError:
            pass

        start_time = event['start'].isoformat()
        end_time = event['end'].isoformat()
        print('Getting events based on event time')
        events_result = self.service.events().list(calendarId=calendar_ids['general'], maxResults=10,
                                                   timeMin=start_time, timeMax=end_time,
                                                   singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        if events:
            print("Select event:")
            for i, event_ob in enumerate(events):
                print(f"  {i + 1}: {event_ob['summary']}")

            choice = int(input("Pick"))
            if 0 < choice <= len(events):
                print("Found event using time")
                return events[choice - 1]

        print('Getting events based on search query')
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = self.service.events().list(calendarId=calendar_ids['general'], maxResults=10,
                                                   timeMin=now, q=event['name'],
                                                   singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        if events:
            print("Select event:")
            for i, event_ob in enumerate(events):
                print(f"  {i + 1}: {event_ob['summary']}")

            choice = int(input("Pick"))
            if 0 < choice <= len(events):
                print("Found event using time")
                return events[choice - 1]

        return None



def get_service() -> Resource:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        return build('calendar', 'v3', credentials=creds)

    except HttpError as error:
        print(f'An error occurred: {error}')


def get_calendars(service: Resource):
    try:
        calendar_list_wrap = service.calendarList().list().execute()
        calendar_list = calendar_list_wrap.get('items', [])
        return calendar_list
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    try:
        service = get_service()

        get_calendars(service)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId=calendar_ids['general'], timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

    except HttpError as error:
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()
