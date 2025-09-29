import os
import pickle

import pandas as pd
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# Google Calendar API setup from gauth.py
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def authenticate_google_calendar():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("calendar", "v3", credentials=creds)


class CalendarManager:
    """
    Manages interactions with the Google Calendar API, including creating calendars,
    and handling events.
    """

    def __init__(self, service: Resource) -> None:
        self.service = service

    def list_calendars(self):
        """Lists all calendars for the authenticated user."""
        return self.service.calendarList().list().execute()  # pyright: ignore[reportAttributeAccessIssue]

    def get_calendar_id_by_name(self, name):
        """
        Finds a calendar by its summary name and returns its ID.

        Args:
            name (str): The summary name of the calendar.
        Returns:
            str: The ID of the found calendar, or None if not found.
        """
        try:
            for item in self.list_calendars()["items"]:
                if item["summary"] == name:
                    return item["id"]
        except Exception as e:
            print(f"Error listing calendars: {e}")
        return None

    def find_or_create_calendar(self, name):
        """
        Finds a calendar by name. If it doesn't exist, it creates a new one
        and applies the specified reminder rules.

        Args:
            name (str): The name of the calendar to find or create.
        Returns:
            str: The ID of the calendar.
        """
        calendar_id = self.get_calendar_id_by_name(name)
        if calendar_id:
            print(f'Found existing calendar "{name}".')
            return calendar_id
        else:
            print(f'Calendar "{name}" not found. Creating a new one...')
            calendar = {
                "summary": name,
                "timeZone": "America/New_York",  # Change to your local time zone
            }
            created_calendar = self.service.calendars().insert(body=calendar).execute()  # pyright: ignore[reportAttributeAccessIssue]

            # Set the reminder rules for the new calendar
            reminders = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 14 * 24 * 60},  # 2 weeks
                    {"method": "popup", "minutes": 2 * 24 * 60},  # 2 days
                    {"method": "popup", "minutes": 0},  # Same day at 9 AM
                ],
            }
            # Update the calendar with the reminders
            self.service.calendarList().update(  # pyright: ignore[reportAttributeAccessIssue]
                calendarId=created_calendar["id"],
                body={"defaultReminders": reminders["overrides"]},
            ).execute()

            print(f'Successfully created calendar "{name}".')
            return created_calendar["id"]

    def list_events(self, calendar_id):
        """
        Lists all events from a given calendar.

        Args:
            calendar_id (str): The ID of the calendar.
        Returns:
            list: A list of events.
        """
        try:
            return self.service.events().list(calendarId=calendar_id).execute()["items"]  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as e:
            print(f"Error listing events for calendar ID {calendar_id}: {e}")
            return []

    def get_event(self, calendar_id, event_id):
        """
        Retrieves a single event by its ID.
        """
        try:
            return (
                self.service.events()  # pyright: ignore[reportAttributeAccessIssue]
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )
        except Exception as e:
            print(f"Error retrieving event ID {event_id}: {e}")
            return None

    def event_exists(self, calendar_id, event_id):
        """
        Checks if an event with the given ID exists in the calendar.

        Args:
            calendar_id (str): The ID of the calendar.
            event_id (str): The ID of the event to check.
        Returns:
            bool: True if the event exists, False otherwise.
        """
        if not event_id or pd.isna(event_id):
            return False

        try:
            self.service.events().get(
                calendarId=calendar_id, eventId=event_id
            ).execute()  # pyright: ignore[reportAttributeAccessIssue]
            return True
        except Exception:
            return False

    def add_event(self, calendar_id, summary, date, description=None):
        """
        Adds a single, all-day event to the calendar with recurring annual reminders.

        Args:
            calendar_id (str): The ID of the calendar.
            summary (str): The summary/title of the event.
            date (str): The date of the event in 'YYYY-MM-DD' format.
            description (str, optional): A description for the event.
        """
        event = {
            "summary": summary,
            "start": {"date": date},
            "end": {"date": date},
            "description": description,
            "recurrence": ["RRULE:FREQ=YEARLY"],
            "reminders": {
                "useDefault": True,
            },
        }

        try:
            self.service.events().insert(calendarId=calendar_id, body=event).execute()  # pyright: ignore[reportAttributeAccessIssue]
            print(f'Successfully added event "{summary}" on {date}.')
        except Exception as e:
            print(f"Error adding event: {e}")

    def update_event(
        self, calendar_id, event_id, summary=None, date=None, description=None
    ):
        """
        Updates an existing event with new details.

        Args:
            calendar_id (str): The ID of the calendar.
            event_id (str): The ID of the event to update.
            summary (str, optional): The new summary.
            date (str, optional): The new date in 'YYYY-MM-DD' format.
            description (str, optional): The new description.
        """
        event = self.get_event(calendar_id, event_id)
        if not event:
            return

        if summary:
            event["summary"] = summary
        if date:
            event["start"]["date"] = date
            event["end"]["date"] = date
        if description:
            event["description"] = description

        try:
            self.service.events().update(  # pyright: ignore[reportAttributeAccessIssue]
                calendarId=calendar_id, eventId=event_id, body=event
            ).execute()
            print(f"Successfully updated event ID {event_id}.")
        except Exception as e:
            print(f"Error updating event ID {event_id}: {e}")

    def delete_event(self, calendar_id, event_id):
        """
        Deletes an event from the calendar.

        Args:
            calendar_id (str): The ID of the calendar.
            event_id (str): The ID of the event to delete.
        """
        try:
            self.service.events().delete(  # pyright: ignore[reportAttributeAccessIssue]
                calendarId=calendar_id, eventId=event_id
            ).execute()
            print(f"Successfully deleted event ID {event_id}.")
        except Exception as e:
            print(f"Error deleting event ID {event_id}: {e}")

    def export_to_csv(self, calendar_id, file_path):
        """
        Exports all events from a calendar to a CSV file.

        Args:
            calendar_id (str): The ID of the calendar.
            file_path (str): The path to the CSV file.
        """
        try:
            events = self.list_events(calendar_id)
            if not events:
                print("No events to export.")
                return

            data = []
            for event in events:
                data.append(
                    {
                        "id": event.get("id"),
                        "summary": event.get("summary", "N/A"),
                        "date": event.get("start", {}).get("date", "N/A"),
                        "description": event.get("description", "N/A"),
                    }
                )

            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
            print(f"Successfully exported {len(events)} events to {file_path}")
        except Exception as e:
            print(f"Error exporting events: {e}")

    def import_from_csv(self, calendar_id, file_path):
        """
        Imports events from a CSV file into a calendar.
        Skips events that already exist if an 'id' column is present in the CSV.

        Args:
            calendar_id (str): The ID of the calendar.
            file_path (str): The path to the CSV file.
        """
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                print("CSV file is empty. Nothing to import.")
                return

            added_count = 0
            skipped_count = 0
            has_id_column = "id" in df.columns

            for _, row in df.iterrows():
                summary = row["summary"]
                date = row["date"]
                description = row["description"]

                # Check if event already exists (if ID is provided)
                if has_id_column:
                    event_id = row.get("id")
                    if self.event_exists(calendar_id, event_id):
                        print(
                            f'Event "{summary}" (ID: {event_id}) already exists. Skipping.'
                        )
                        skipped_count += 1
                        continue

                # Add the event
                self.add_event(calendar_id, summary, date, description)
                added_count += 1

            print(
                f"Import completed: {added_count} events added, {skipped_count} events skipped (already exist)"
            )
        except FileNotFoundError:
            print(f"Error: The file {file_path} was not found.")
        except Exception as e:
            print(f"Error importing events: {e}")
