import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource
import base32hex

from utils import DEFAULT_TZ, DEFAULT_TZ_STR

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


calendar_ids = {
    'testing': 'primary',
    'general': 'q3bdd3oa0qmdk3k7plvug31u6c@group.calendar.google.com',
    'danszusjes': 'b94dllo4lfb6garktd0dlh05io@group.calendar.google.com',
    'ballroom': 'stgo5dh75karln6v7c68b8u8d4@group.calendar.google.com',
    'argentine tango': '0tl34lgpbpmgncb5t400kfgsjs@group.calendar.google.com',
    'lindy hop': 'c_45072b8c924f957e972bc1e0aca3360eb7bb9c87802cf9b0bda9a7a69dc33cbe@group.calendar.google.com',
}


class CalendarAdapter:
    def __init__(self):
        self.service = get_service()

    @staticmethod
    def event_id(event: dict) -> str:
        return base32hex.b32encode(event['slug'].encode()).lower()[:-3]

    @staticmethod
    def g_event_from_event(event: dict, category: str = "") -> dict:
        """
        Create a dictionary in Google Calendar format from event info.

        :param event: Source event info
        :param category: Category to make the dict for
        :return: Event info in Calendar format
        """
        event_name = f"BSS {event['name']}" if category == 'danszusjes' else event['name']

        description = event['content'].replace('\n', '')  # \n also gets interpreted as enters, we don't want that
        # Add link to webpage at the bottom
        description += f"<p><strong>Website event page<br /></strong><a href='{event['link']}'>{event['link']}</a></p>"

        event = {
            'summary': event_name,
            'location': f"{event['venue']}, {event['address']}",
            'description': description,
            'start': {
                'dateTime': event['start'].isoformat(),
                'timeZone': DEFAULT_TZ_STR,
            },
            'end': {
                'dateTime': event['end'].isoformat(),
                'timeZone': DEFAULT_TZ_STR,
            },
        }
        return event

    def do_event(self, event: dict) -> list[dict]:
        """
        Make sure a given event is present (created/updated) for all relevant event categories.

        :param event: Event information
        :return: Calendar events
        """
        categories = ['general', 'danszusjes'] + list(event['categories'])
        g_events = []

        for category in categories:
            if calendar_ids.get(category) is None:
                continue
            g_event = self.find_event(event, category)
            if g_event is None:
                g_event = self.create_event(event, category)
            else:
                g_event = self.update_event(event, g_event, category)
            g_events.append(g_event)

        return g_events

    def create_event(self, event: dict, category: str = "general") -> dict:
        """
        Creates a Google Calendar event based on the info in `event`

        :param event: Source info
        :param category: Calendar category the event is for
        :return: Created Calendar event
        """
        g_event_data = self.g_event_from_event(event, category)
        g_event_data['id'] = self.event_id(event)

        g_event = self.service.events().insert(calendarId=calendar_ids[category], body=g_event_data).execute()
        print(f"Calendar: Event created in {category} calendar: {g_event.get('htmlLink')}")
        return g_event

    def update_event(self, event: dict, g_event: dict, category: str = "general") -> dict:
        """
        Updates the details of a given Google Calendar event to match the info in `event`

        :param event: Source info
        :param g_event: Calendar event to update
        :param category: Calendar category the event is from
        :return: Updated Calendar event
        """
        g_event_data = self.g_event_from_event(event, category)
        g_event_data['id'] = g_event['id']

        g_event = self.service.events()\
            .update(calendarId=calendar_ids[category], eventId=g_event['id'], body=g_event_data)\
            .execute()
        print(f"Calendar: Event updated in {category} calendar: {g_event.get('htmlLink')}")
        return g_event

    @staticmethod
    def _select_event(g_events: list[dict], event: dict, method: str) -> dict | None:
        """
        Automatically or manually selects a Calendar event from a list.

        :param g_events: Events to choose from
        :param event: Source info to look for (mainly name)
        :param method: What method was used to find this list, to print
        :return: Selected event
        """
        if not g_events:
            print("nothing")
            return None

        auto_choice = None
        for i, event_ob in enumerate(g_events):
            if event['name'] in event_ob['summary']:
                auto_choice = i
                break

        if auto_choice is not None:
            print("found event automatically")
            return g_events[auto_choice]

        print("\nCalendar: Select event to update:\n   0 for not included, create new one")
        for i, event_ob in enumerate(g_events):
            print(f"  {i + 1}: {event_ob['summary']}")

        choice = int(input("Pick: "))
        if 0 < choice <= len(g_events):
            print(f"Calendar: Found event using {method}")
            return g_events[choice - 1]

    def find_event(self, event: dict, category: str = "general") -> dict | None:
        """
        Search the calendar identified by `category` for a match of `event`.

        :param event: Source event to find a match for
        :param category: Calendar to search in
        :return: Event, if found
        """
        supposed_id = self.event_id(event)
        try:
            event_ob = self.service.events().get(calendarId=calendar_ids[category], eventId=supposed_id).execute()
            print("Calendar: Found event using id")
            return event_ob
        except HttpError:
            pass

        print('Calendar: Searching events based on event time... ', end='')
        start_time = event['start'].isoformat()
        end_time = event['end'].isoformat()
        events_result = self.service.events().list(calendarId=calendar_ids[category], maxResults=10,
                                                   timeMin=start_time, timeMax=end_time,
                                                   singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        chosen_event = self._select_event(events, event, "time")
        if chosen_event is not None:
            return chosen_event

        print('Calendar: Searching events based on search query... ')
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = self.service.events().list(calendarId=calendar_ids[category], maxResults=10,
                                                   timeMin=now, q=event['name'],
                                                   singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        chosen_event = self._select_event(events, event, "search")
        if chosen_event is not None:
            return chosen_event

        return None


def get_service() -> Resource:
    """
    Do authorization and get a resource object.

    :return: Calendar resource
    """
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
                'google_api_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        return build('calendar', 'v3', credentials=creds)

    except HttpError as error:
        print(f'Calendar: An error occurred: {error}')


def get_calendars(service: Resource):
    try:
        calendar_list_wrap = service.calendarList().list().execute()
        calendar_list = calendar_list_wrap.get('items', [])
        return calendar_list
    except HttpError as error:
        print(f'Calendar: An error occurred: {error}')
        return []


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    try:
        service = get_service()

        calendars = get_calendars(service)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Calendar: Getting the upcoming 10 events')
        events_result = service.events().list(calendarId=calendar_ids['general'], timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('Calendar: No upcoming events found.')
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

    except HttpError as error:
        print(f'Calendar: An error occurred: {error}')


if __name__ == '__main__':
    main()
