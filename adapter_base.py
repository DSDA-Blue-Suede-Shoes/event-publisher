import logging
from abc import ABC, abstractmethod

from seleniumrequests import Firefox


def login_required(func):
    def inner(*args, **kwargs):
        self = args[0]
        if not self.logged_in:
            self.login()
        return func(*args, **kwargs)
    return inner


class AdapterBase(ABC):
    def __init__(self, driver: Firefox, name: str):
        self.driver = driver
        self.__name = name
        self.logged_in = False

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def get_events(self):
        pass

    @abstractmethod
    @login_required
    def create_event(self, event: dict):
        pass

    @abstractmethod
    @login_required
    def update_event(self, event: dict, existing_event: dict):
        pass

    def _select_event(self, platform_events: list[dict], event: dict) -> dict | None:
        """
        Automatically or manually selects a platform event from a list.

        :param platform_events: Events to choose from
        :param event: Source info to look for (mainly name)
        :return: Selected event
        """
        if not platform_events:
            return None

        auto_choice = self._select_event_auto(platform_events, event)
        if auto_choice is not None:
            return auto_choice

        return self._select_event_manual(platform_events)

    def _select_event_auto(self, platform_events: list[dict], event: dict, log=True) -> dict | None:
        """
        Automatically or select a platform event from a list.

        :param platform_events: Events to choose from
        :param event: Source info to look for (mainly name)
        :return: Selected event
        """
        if not platform_events:
            return None

        auto_choice = None
        for i, facebook_event in enumerate(platform_events):
            if event['name'] in facebook_event['name']:
                auto_choice = i
                break

        if auto_choice is not None:
            if log:
                print(f"{self.__name}: Found event automatically!")
            return platform_events[auto_choice]

        return None

    def _select_event_manual(self, platform_events: list[dict]) -> dict | None:
        """
        Manually select a platform event from a list.

        :param platform_events: Events to choose from
        :return: Selected event
        """
        print(f"{self.__name}: Select event to update:\n  0 for not included, create new one")

        events_to_display = 20
        for i, facebook_event in enumerate(platform_events):
            print(f"  {i + 1}: {facebook_event['name']}")
            if i == events_to_display - 1:
                break

        choice = int(input("Pick"))
        if 0 < choice <= min(len(platform_events), events_to_display):
            print(f"{self.__name}: Chosen {platform_events[choice - 1]['name']}")
            return platform_events[choice - 1]

        return None

    def do_event(self, event: dict) -> bool:
        """
        Make sure a given event is present (created/updated) on the platform.

        :param event: Event information
        :return: New/updated event
        """
        try:
            platform_events = self.get_events()
            existing_event = self._select_event(platform_events, event)
            if existing_event:
                return self.update_event(event, existing_event)
            return self.create_event(event)
        except BaseException:
            logging.exception(f"Something went wrong processing {event['name']}")
