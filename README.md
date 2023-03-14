# Event Publisher

This project strives to automate the process of publishing events from the D.S.D.A. Blue Suede Shoes website ([events page](https://dsda.nl/events/)) to several platforms. Notably, the various Google Calendars for different dance styles and [danszusjes.nl](https://danszusjes.nl), [Unilife](https://unilife.nl), and [Facebook](https://www.facebook.com/Bluesuedeshoesdelft).

The project is in reasonable usability and documentation state, but not super robust against errors.

## Setting up
Get a Python environment, e.g. a virtual one:

```shell
python -m venv ./venv
```

Install the requirements

```shell
pip install -r requirements.txt
```

Get the authentication information for the various platforms. Likely an existing config can mostly be reused by someone else.

* Google Calendar: Get credentials as [explained here](https://developers.google.com/calendar/api/quickstart/python). Get a `credentials.json` file, rename to `google_api_credentials.json`.
* Unilife: Email address and password in `credentials.json`.
* Facebook:
  * Email address, password, and two-factor authentication info (OTP)
  * A token for the Graph API. See "Before You Start" on the [getting started page](https://developers.facebook.com/docs/graph-api/get-started#before-you-start).
  * These also in `credentials.json`.

Example `credentials.json`
```json
{
  "FACEBOOK_ID": "",
  "FACEBOOK_PASSWORD": "",
  "FACEBOOK_TOTP": "",
  "UNILIFE_ID": "",
  "UNILIFE_PASSWORD": "",
  "FACEBOOK_GRAPH_API_TOKEN": ""
}
```

## How to use
Run the Python program.
```shell
./venv/Scripts/activate
python main.py
```
The terminal will guide you through the process.
