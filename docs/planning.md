Requirements for what I need to be able to do:
- read/fetch/view events per calendar: all historical; so if i want events for calendarA, it will give all historial events from beginning of time
- read/fetch/view events across all calendars
- be able to filter events by attributes: sometimes I don't want to fetch all historical, but events from particular calendar where some condition holds
    - this can be string/text matching conditions on the name/description of the event
    - can be comparator conditions on the start/end date/times of events
    - can be comparator? conditions on the location of events (lets leave this out to start with it seems hard)
    - this can be the recurrence rules defined on each event; like "get me all events from calendarA where the event occurs weekly" or anything else related to the recurring aspect of an event
- to save a view of fetched&filtered results as csv or json or something: self-explanatory
- to set/modify properties of events: heres an example
    - "in calendarA, for every event that has 'Anniversary' in the same, set the reminders to [1 month before, 1 week before, 1 day before]"
    - in order to enable 'dry-run' tests, i want an explicit command that commits the modifications (which actually calls the PATCH endpoints under the hood)
- to move/transfer/copy events from one calendar to another: self-explanatory


I want to be able to do some complex stuff like:
- set a reminder rule for a calendar, and then assert all events on that calendar follow that reminder rule (or coerce them to if they don't)
- set up a series of 8 named checkpoints (like 'Checkpoint {i}/8') starting on friday and spaced 3 weeks apart, and set a 3 day reminder for each
- create a calendar called "Birthdays" if it doesn't exist, set its default notification/reminders to 2 weeks before event & on day of event. Then transfer all events with "Birthday" in the name across all OTHER calendars to the Birthday calendar, and set every event on the Birthday calendar to recur yearly


Heres some script examples of what I want to be able to do

```
# this just produces all historial events on CalA and exports to csv and json

calendar[CalA] .events >> export -c "some_path.csv" -j "some_path.json"
```

```
# this is some process with filters and modification of the events on the calendar, and then copying the results to another archival calendar

calendar[CalA] > events 
    | where name match 'some regex' 
    | where start < 2025-01-01 
    | set description = "some test description of event" 
    | set recurrence = clear
    | set reminders = clear
> copy calendar[Archive - CalA]
```

```
# newlines don't matter. example of transferring all anniversaries/birthdays from CalA to SpecialCal and applying a yearly recurrence rule and reminders one week and one day before the event.

calendar[CalA] > events 
    | where (name match '(?i)anniversary' or name match '(?i)birthday')
    | set description = "this is an anniversary or bday" 
    | set recurrence = year 
    | set reminders = 1 week, 1 day 
> transfer calendar[SpecialCal]
```

```
// example of adding a simple event

calendar[CalA] > add
    | set name = "My Event"
    | set description = "This is an example event"
    | set start = 2025-12-09T11:00:00
    | set end = 2025-12-09T14:00:00
    | set reminders = 2 days
```


```
// example of generating a series of events (just doing a dry run to see what the result would be). Ofcourse the script checker will have to make sure the number of elements of idx match the number of elements of .offsets

calendar[CalA] > series
    | set idx = (1,2,3,4,5)
    | set name = "Meeting %idx/5"
    | set offsets = 0 days,3 days, 1 week,2 weeks, 24 days, 1 month
    | set reminders = 0 days

```