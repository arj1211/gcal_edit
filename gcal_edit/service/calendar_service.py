import os
import pickle
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_TIMEZONE = "UTC"


def authenticate_google_calendar() -> Resource:
    creds = None
    if os.path.exists("secrets/token.pickle"):
        with open("secrets/token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "secrets/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("secrets/token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("calendar", "v3", credentials=creds)


class CalendarManager:
    """Calendar helpers shared by the CLI and Textual UI."""

    def __init__(self, service: Resource) -> None:
        self.service = service

    def _collect_pages(
        self,
        method: Callable[..., Any],
        *,
        items_key: str = "items",
        max_results: Optional[int] = None,
        **params: Any,
    ) -> List[Dict[str, Any]]:
        accumulated: List[Dict[str, Any]] = []
        page_token = params.pop("pageToken", None)
        while True:
            call_params = {k: v for k, v in params.items() if v is not None}
            if page_token:
                call_params["pageToken"] = page_token
            response = method(**call_params).execute()
            page_items = response.get(items_key, [])
            if max_results:
                remaining = max_results - len(accumulated)
                if remaining <= 0:
                    return accumulated[:max_results]
                page_items = page_items[:remaining]
            accumulated.extend(page_items)
            if max_results and len(accumulated) >= max_results:
                return accumulated[:max_results]
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return accumulated

    def list_calendars(
        self,
        *,
        max_results: Optional[int] = 250,
        min_access_role: Optional[str] = None,
        show_hidden: bool = False,
        show_deleted: bool = False,
        sync_token: Optional[str] = None,
        time_zone: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "minAccessRole": min_access_role,
            "showHidden": show_hidden,
            "showDeleted": show_deleted,
            "syncToken": sync_token,
            "timeZone": time_zone,
        }
        if max_results:
            params["maxResults"] = max_results
        return self._collect_pages(
            self.service.calendarList().list,
            items_key="items",
            **{k: v for k, v in params.items() if v is not None},
        )

    def get_calendar_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            return next(
                item
                for item in self.list_calendars()
                if item.get("summary", "").lower() == name.lower()
            )
        except StopIteration:
            return None

    def ensure_calendar(
        self,
        name: str,
        time_zone: str = DEFAULT_TIMEZONE,
        reminders: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        calendar = self.get_calendar_by_name(name)
        if calendar:
            return calendar.get("id")

        calendar_body = {"summary": name, "timeZone": time_zone}
        created_calendar = self.service.calendars().insert(body=calendar_body).execute()
        calendar_id = created_calendar.get("id")

        if calendar_id and reminders:
            self.service.calendarList().update(
                calendarId=calendar_id, body={"defaultReminders": reminders}
            ).execute()
        return calendar_id

    def list_events(
        self,
        calendar_id: str,
        *,
        max_results: Optional[int] = 5000,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        single_events: bool = False,
        order_by: Optional[str] = None,
        query: Optional[str] = None,
        show_deleted: bool = False,
        show_hidden_invitations: bool = False,
        i_cal_uid: Optional[str] = None,
        updated_min: Optional[str] = None,
        sync_token: Optional[str] = None,
        time_zone: Optional[str] = None,
        always_include_email: bool = False,
    ) -> List[Dict[str, Any]]:
        if sync_token and updated_min:
            raise ValueError("sync_token cannot be combined with updated_min")
        params: Dict[str, Any] = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": single_events,
            "orderBy": order_by,
            "q": query,
            "showDeleted": show_deleted,
            "showHiddenInvitations": show_hidden_invitations,
            "iCalUID": i_cal_uid,
            "updatedMin": updated_min,
            "syncToken": sync_token,
            "timeZone": time_zone,
            "alwaysIncludeEmail": always_include_email,
        }
        if max_results:
            params["maxResults"] = max_results
        return self._collect_pages(
            self.service.events().list,
            items_key="items",
            max_results=max_results,
            calendarId=calendar_id,
            **{k: v for k, v in params.items() if v is not None},
        )

    def list_events_page(
        self,
        calendar_id: str,
        *,
        max_results: Optional[int] = None,
        page_token: Optional[str] = None,
        **kwargs: Any,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
        params: Dict[str, Any] = {"calendarId": calendar_id}
        if max_results:
            params["maxResults"] = max_results
        if page_token:
            params["pageToken"] = page_token
        params.update({k: v for k, v in kwargs.items() if v is not None})
        response = self.service.events().list(**params).execute()
        return (
            response.get("items", []),
            response.get("nextPageToken"),
            response.get("nextSyncToken"),
        )

    def get_event(self, calendar_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        try:
            return (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )
        except Exception as exc:
            print(f"Error retrieving event {event_id}: {exc}")
            return None

    def event_exists(self, calendar_id: str, event_id: Optional[str]) -> bool:
        if not event_id or pd.isna(event_id):
            return False
        try:
            self.service.events().get(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            return True
        except Exception:
            return False

    def _clean_for_copy(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "summary": event.get("summary"),
            "description": event.get("description"),
            "start": event.get("start"),
            "end": event.get("end"),
            "recurrence": event.get("recurrence"),
            "reminders": event.get("reminders"),
        }
        return {key: value for key, value in payload.items() if value is not None}

    def _create_event_payload(
        self,
        summary: str,
        date: str,
        description: Optional[str],
        recurrence: Optional[List[str]],
        reminders: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        event_payload = {
            "summary": summary,
            "start": {"date": date},
            "end": {"date": date},
            "description": description,
        }
        if recurrence:
            event_payload["recurrence"] = recurrence
        if reminders:
            event_payload["reminders"] = {"useDefault": False, "overrides": reminders}
        return event_payload

    def add_event(
        self,
        calendar_id: str,
        summary: str,
        date: str,
        description: Optional[str] = None,
        recurrence: Optional[List[str]] = None,
        reminders: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        event_payload = self._create_event_payload(
            summary=summary,
            date=date,
            description=description,
            recurrence=recurrence,
            reminders=reminders,
        )
        try:
            created_event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=event_payload)
                .execute()
            )
            return created_event.get("id")
        except Exception as exc:
            print(f"Error adding event '{summary}': {exc}")
            return None

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        summary: Optional[str] = None,
        date: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        event = self.get_event(calendar_id, event_id)
        if not event:
            return False

        if summary:
            event["summary"] = summary
        if date:
            event.setdefault("start", {})["date"] = date
            event.setdefault("end", {})["date"] = date
        if description is not None:
            event["description"] = description

        try:
            self.service.events().update(
                calendarId=calendar_id, eventId=event_id, body=event
            ).execute()
            return True
        except Exception as exc:
            print(f"Error updating event {event_id}: {exc}")
            return False

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            return True
        except Exception as exc:
            print(f"Error deleting event {event_id}: {exc}")
            return False

    def transfer_event(
        self,
        source_calendar_id: str,
        dest_calendar_id: str,
        event_id: str,
        delete_source: bool = False,
    ) -> Optional[str]:
        event = self.get_event(source_calendar_id, event_id)
        if not event:
            return None
        payload = self._clean_for_copy(event)
        try:
            inserted_event = (
                self.service.events()
                .insert(calendarId=dest_calendar_id, body=payload)
                .execute()
            )
            if delete_source:
                self.delete_event(source_calendar_id, event_id)
            return inserted_event.get("id")
        except Exception as exc:
            print(f"Error transferring event {event_id}: {exc}")
            return None

    def export_to_csv(self, calendar_id: str, file_path: str) -> bool:
        try:
            events = self.list_events(calendar_id)
            if not events:
                print("No events to export.")
                return False
            data = [
                {
                    "id": event.get("id"),
                    "summary": event.get("summary"),
                    "date": event.get("start", {}).get("date"),
                    "description": event.get("description"),
                }
                for event in events
            ]
            pd.DataFrame(data).to_csv(file_path, index=False)
            return True
        except Exception as exc:
            print(f"Error exporting events: {exc}")
            return False

    def import_from_csv(
        self,
        calendar_id: str,
        file_path: str,
        recurrence: Optional[List[str]] = None,
        reminders: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        stats = {"added": 0, "skipped": 0}
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return stats
            has_id_column = "id" in df.columns
            for _, row in df.iterrows():
                summary = row.get("summary")
                date = row.get("date")
                description = row.get("description")
                if not summary or not date:
                    stats["skipped"] += 1
                    continue
                if has_id_column and self.event_exists(calendar_id, row.get("id")):
                    stats["skipped"] += 1
                    continue
                if self.add_event(
                    calendar_id,
                    summary,
                    date,
                    description=description,
                    recurrence=recurrence,
                    reminders=reminders,
                ):
                    stats["added"] += 1
            return stats
        except FileNotFoundError:
            print(f"Error: {file_path} not found.")
            return stats
        except Exception as exc:
            print(f"Error importing events: {exc}")
            return stats

    def batch_edit_from_csv(
        self,
        calendar_id: str,
        file_path: str,
        recurrence: Optional[List[str]] = None,
        reminders: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0}
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return stats
            for _, row in df.iterrows():
                action = str(row.get("action", "")).strip().lower()
                event_id = row.get("id")
                summary = row.get("summary")
                date = row.get("date")
                description = row.get("description")
                if action == "add":
                    if not summary or not date:
                        stats["skipped"] += 1
                        continue
                    if self.add_event(
                        calendar_id,
                        summary,
                        date,
                        description=description,
                        recurrence=recurrence,
                        reminders=reminders,
                    ):
                        stats["added"] += 1
                elif action == "update":
                    if event_id and self.update_event(
                        calendar_id,
                        event_id,
                        summary=summary,
                        date=date,
                        description=description,
                    ):
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                elif action == "delete":
                    if event_id and self.delete_event(calendar_id, event_id):
                        stats["deleted"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    stats["skipped"] += 1
            return stats
        except FileNotFoundError:
            print(f"Error: {file_path} not found.")
            return stats
        except Exception as exc:
            print(f"Error during batch edit: {exc}")
            return stats
