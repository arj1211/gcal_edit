# Special Dates Manager
A Python-based command-line application for managing and tracking important dates like birthdays and anniversaries. This tool leverages the Google Calendar API to provide a seamless and persistent way to organize your special dates, with automated yearly reminders to ensure you never miss a significant moment.

## Key Features
- **Google Calendar Integration:** Automatically creates a dedicated "Special Dates" calendar in your Google account.

- **Event Management:** Add, list, edit, and delete special dates directly from your terminal.

- **Annual Reminders:** Events are set to recur annually with popup reminders configured for 2 weeks, 2 days, and on the date itself.

- **Data Portability:** Easily export all your special dates to a CSV file or import them from an existing CSV, making it simple to back up or migrate your data.

- **User-Friendly CLI:** An interactive, menu-driven interface guides you through all available actions.


## Set up Google Calendar API credentials

- Follow the official Google API documentation to create a project and enable the Google Calendar API.

Download your `credentials.json` file and place it in the project's root directory.

## Usage
Run the main script using [`uv`](https://docs.astral.sh/uv/) to start the interactive menu:

```bash
uv run main.py
```

Follow the on-screen prompts to manage your special dates. The application will handle the authentication process for you on the first run.