import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_service():
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


def get_calendars(service):
    try:
        calendar_list_wrap = service.calendarList().list().execute()
        calendar_list = calendar_list_wrap.get('items', [])
        return calendar_list
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []


def create_event(service, event):
    event = {
        'summary': event['title'],
        'location': event['location'],
        'description': event['content'],
        'start': {
            'dateTime': event['start'].isoformat(),
            'timeZone': 'Europe/Brussels',
        },
        'end': {
            'dateTime': event['end'].isoformat(),
            'timeZone': 'Europe/Brussels',
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Event created: {event.get('htmlLink')}")


calendar_ids = {
    'general': 'q3bdd3oa0qmdk3k7plvug31u6c@group.calendar.google.com',
    'ballroom': 'stgo5dh75karln6v7c68b8u8d4@group.calendar.google.com',
    'tango': '0tl34lgpbpmgncb5t400kfgsjs@group.calendar.google.com',
    'lindy': 'c_45072b8c924f957e972bc1e0aca3360eb7bb9c87802cf9b0bda9a7a69dc33cbe@group.calendar.google.com',
}


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    try:
        service = get_service()

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
