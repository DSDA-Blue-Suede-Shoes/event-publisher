from pathlib import Path

import pytz
DEFAULT_TZ_STR = 'Europe/Brussels'
DEFAULT_TZ = pytz.timezone(DEFAULT_TZ_STR)

project_dir = Path(__file__).parent
runtime_data_folder = project_dir / "runtime_data"


def ask_confirmation(query):
    result = True
    while True:
        response = input(f"{query} [y]/n ")
        if response == '':
            break
        elif response[0] == 'y':
            result = True
            break
        elif response[0] == 'n':
            result = False
            break

    return result
