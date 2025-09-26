import sys

from calendar_service import CalendarManager, authenticate_google_calendar


def get_user_input(prompt, required=True):
    """Utility function to get user input with a prompt."""
    while True:
        user_input = input(f"{prompt}: ").strip()
        if required and not user_input:
            print("This field is required. Please try again.")
        else:
            return user_input


def add_special_date(manager, calendar_id):
    """Handles the 'Add a new special date' option."""
    print("\n--- Add New Special Date ---")
    name = get_user_input("Enter the name of the special date (e.g., Mom's Birthday)")
    date = get_user_input("Enter the date (YYYY-MM-DD)")
    description = get_user_input("Enter a description (optional)", required=False)

    manager.add_event(calendar_id, name, date, description)


def list_special_dates(manager, calendar_id):
    """Handles the 'List all special dates' option."""
    print("\n--- All Special Dates ---")
    events = manager.list_events(calendar_id)
    if events:
        for i, event in enumerate(events, 1):
            print(f"{i}. Event ID: {event.get('id')}")
            print(f"   Name: {event.get('summary')}")
            print(f"   Date: {event.get('start', {}).get('date')}")
            print(f"   Description: {event.get('description', 'No description')}")
            print("-" * 20)
    else:
        print("No special dates found.")


def edit_special_date(manager, calendar_id):
    """Handles the 'Edit an existing special date' option."""
    print("\n--- Edit Special Date ---")
    events = manager.list_events(calendar_id)
    if not events:
        print("No special dates to edit.")
        return

    list_special_dates(manager, calendar_id)

    event_id = get_user_input("Enter the ID of the event you want to edit")

    try:
        event = manager.get_event(calendar_id, event_id)
        if not event:
            print("Event not found. Please check the ID and try again.")
            return

        print(f"Editing event: {event.get('summary')}")
        new_name = get_user_input(
            f"Enter new name (current: {event.get('summary')})", required=False
        )
        new_date = get_user_input(
            f"Enter new date (current: {event.get('start', {}).get('date')})",
            required=False,
        )
        new_description = get_user_input(
            f"Enter new description (current: {event.get('description', 'No description')})",
            required=False,
        )

        manager.update_event(
            calendar_id,
            event_id,
            summary=new_name if new_name else event.get("summary"),
            date=new_date if new_date else event.get("start", {}).get("date"),
            description=new_description
            if new_description
            else event.get("description"),
        )
    except Exception as e:
        print(f"An error occurred while editing: {e}")


def delete_special_date(manager, calendar_id):
    """Handles the 'Delete a special date' option."""
    print("\n--- Delete Special Date ---")
    events = manager.list_events(calendar_id)
    if not events:
        print("No special dates to delete.")
        return

    list_special_dates(manager, calendar_id)

    event_id = get_user_input("Enter the ID of the event you want to delete")

    if event_id:
        confirm = get_user_input(
            f"Are you sure you want to delete event with ID '{event_id}'? (yes/no)"
        ).lower()
        if confirm == "yes":
            manager.delete_event(calendar_id, event_id)
        else:
            print("Deletion cancelled.")


def export_dates_to_csv(manager, calendar_id):
    """Handles the 'Export special dates to CSV' option."""
    print("\n--- Export Special Dates ---")
    file_path = get_user_input(
        "Enter the filename to export to (default is 'special_dates.csv')"
    )
    manager.export_to_csv(calendar_id, file_path or "special_dates.csv")


def import_dates_from_csv(manager, calendar_id):
    """Handles the 'Import special dates from CSV' option."""
    print("\n--- Import Special Dates ---")
    file_path = get_user_input(
        "Enter the filename to import from (default is 'special_dates.csv')"
    )
    manager.import_from_csv(calendar_id, file_path or "special_dates.csv")


def main():
    """
    Main function for the interactive special dates manager.
    """
    try:
        print("--- Special Dates Manager ---")
        service = authenticate_google_calendar()
        manager = CalendarManager(service)

        # Use a consistent calendar name
        calendar_name = "Special Dates"
        calendar_id = manager.find_or_create_calendar(calendar_name)

        if not calendar_id:
            print("Could not find or create a calendar. Exiting.")
            sys.exit(1)

        while True:
            print("\n--- Menu ---")
            print("1. Add a new special date")
            print("2. List all special dates")
            print("3. Edit an existing special date")
            print("4. Delete a special date")
            print("5. Export special dates to CSV")
            print("6. Import special dates from CSV")
            print("7. Exit")

            choice = get_user_input("Enter your choice (1-7)")

            if choice == "1":
                add_special_date(manager, calendar_id)
            elif choice == "2":
                list_special_dates(manager, calendar_id)
            elif choice == "3":
                edit_special_date(manager, calendar_id)
            elif choice == "4":
                delete_special_date(manager, calendar_id)
            elif choice == "5":
                export_dates_to_csv(manager, calendar_id)
            elif choice == "6":
                import_dates_from_csv(manager, calendar_id)
            elif choice == "7":
                print("Exiting. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter a number from 1 to 7.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
