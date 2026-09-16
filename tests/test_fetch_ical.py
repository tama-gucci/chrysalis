"""
Unit tests for Chrysalis Inbound Calendar Ingestion Engine (fetch_ical.py)
========================================================================
Validates RFC 5545 parsing, UTC -> local timezone normalization,
recurrence rule expansion, and safe memory serialization.
"""

import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile

from System.scripts.fetch_ical import (
    unfold_ical_text,
    parse_vevent_blocks,
    parse_tz_offset,
    parse_ical_dt,
    parse_ical_feed,
    update_scheduling_memory,
    serialize_calendar_block
)

MOCK_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Academic & Personal
X-WR-TIMEZONE:America/Chicago
BEGIN:VEVENT
DTSTART:20260909T140000Z
DTEND:20260909T151500Z
UID:single-meeting-1@example.com
SUMMARY:Chemistry 101 Lecture
LOCATION:Hall A, Room 204
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260910
DTEND;VALUE=DATE:20260911
UID:allday-event-1@example.com
SUMMARY:Fall Career Expo
LOCATION:Campus Center
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20260810T190000Z
DTEND:20260810T200000Z
UID:recurring-event-1@example.com
SUMMARY:Weekly TA Office Hours
LOCATION:https://zoom.us/j/123456789
RRULE:FREQ=WEEKLY;BYDAY=WE,FR
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20260909T160000Z
DTEND:20260909T170000Z
UID:cancelled-meeting-1@example.com
SUMMARY:Cancelled Department Seminar
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""

SAMPLE_MEMORY_MD = """---
timezone_offset: "-05:00"

diurnal_baselines:
  weekday_default_wake: "08:30"

calendar_sync:
  enabled: true
  provider: "ical_feed"
  ical_url: ""
  last_sync: null
  horizon_start: null
  horizon_end: null
  cached_events: []

chronotype_telemetry:
  hourly_efficiency_history: []
---

# Operational Memory Notes
"""


class TestFetchIcal(unittest.TestCase):

    def test_line_unfolding(self):
        folded = "SUMMARY:This is a long event title that was folded \r\n across multiple lines\n by the calendar server"
        unfolded = unfold_ical_text(folded)
        self.assertEqual(unfolded, "SUMMARY:This is a long event title that was folded across multiple linesby the calendar server")

    def test_parse_tz_offset(self):
        tz_neg = parse_tz_offset("-05:00")
        self.assertEqual(tz_neg.utcoffset(None), timedelta(hours=-5))
        tz_pos = parse_tz_offset("+02:00")
        self.assertEqual(tz_pos.utcoffset(None), timedelta(hours=2))

    def test_utc_to_local_conversion(self):
        # 14:00 UTC with -05:00 offset should convert to 09:00 local time
        tz = parse_tz_offset("-05:00")
        d, iso_str, all_day = parse_ical_dt("DTSTART:20260909T140000Z", "-05:00", tz)
        self.assertEqual(d, date(2026, 9, 9))
        self.assertFalse(all_day)
        self.assertEqual(iso_str, "2026-09-09T09:00:00-05:00")
        self.assertFalse(iso_str.endswith("Z"), "Constitutional invariant: timestamps must not end in raw 'Z'")

    def test_all_day_parsing(self):
        tz = parse_tz_offset("-05:00")
        d, iso_str, all_day = parse_ical_dt("DTSTART;VALUE=DATE:20260910", "-05:00", tz)
        self.assertEqual(d, date(2026, 9, 10))
        self.assertTrue(all_day)
        self.assertEqual(iso_str, "2026-09-10")

    def test_parse_ical_feed_events(self):
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 15)
        events = parse_ical_feed(MOCK_ICS, start_d, end_d, tz_str="-05:00")
        
        # We expect:
        # 1. Chemistry 101 Lecture on Sept 9 (has_physical_location=True)
        # 2. Weekly TA Office Hours recurring on Wed Sept 9 (has_physical_location=False due to Zoom link)
        # 3. Fall Career Expo on Sept 10 (all_day=True)
        # 4. Weekly TA Office Hours recurring on Fri Sept 11
        # Cancelled meeting should be omitted!
        titles = [e["title"] for e in events]
        self.assertIn("Chemistry 101 Lecture", titles)
        self.assertIn("Fall Career Expo", titles)
        self.assertIn("Weekly TA Office Hours", titles)
        self.assertNotIn("Cancelled Department Seminar", titles)

        # Check physical location heuristics
        chem_event = next(e for e in events if e["title"] == "Chemistry 101 Lecture")
        self.assertTrue(chem_event["has_physical_location"])
        self.assertEqual(chem_event["start"], "2026-09-09T09:00:00-05:00")
        self.assertEqual(chem_event["end"], "2026-09-09T10:15:00-05:00")

        zoom_event = next(e for e in events if e["title"] == "Weekly TA Office Hours")
        self.assertFalse(zoom_event["has_physical_location"])
        self.assertTrue(zoom_event["is_recurring"])

    def test_update_scheduling_memory(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".md", encoding="utf-8") as tf:
            tf.write(SAMPLE_MEMORY_MD)
            temp_path = tf.name

        events = [
            {
                "title": "Advising Appointment",
                "start": "2026-09-09T11:00:00-05:00",
                "end": "2026-09-09T12:00:00-05:00",
                "all_day": False,
                "location": "Dean's Office",
                "has_physical_location": True,
                "is_recurring": False
            }
        ]

        update_scheduling_memory(
            temp_path,
            events,
            ical_url="https://calendar.google.com/test.ics",
            tz_str="-05:00",
            start_str="2026-09-08",
            end_str="2026-09-15"
        )

        content = Path(temp_path).read_text(encoding="utf-8")
        self.assertIn('provider: "ical_feed"', content)
        self.assertIn('ical_url: "https://calendar.google.com/test.ics"', content)
        self.assertIn("Advising Appointment", content)
        self.assertIn("Dean's Office", content)
        self.assertIn("chronotype_telemetry:", content)
        self.assertIn("# Operational Memory Notes", content)

    def test_rrule_until_pre_pruning(self):
        """Historical recurrences whose UNTIL is before start_date must be pre-pruned."""
        ics_expired = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20151109T174500Z
RRULE:FREQ=WEEKLY;UNTIL=20151130T234500Z;BYDAY=MO
UID:expired-job-shift@example.com
SUMMARY:Old Shift
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 15)
        events = parse_ical_feed(ics_expired, start_d, end_d, tz_str="-05:00")
        self.assertEqual(len(events), 0, "Expired series before start_date must be pruned")

    def test_rrule_until_active_window(self):
        """Recurrences bounded by UNTIL must stop producing events after UNTIL date."""
        ics_until = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260909T140000Z
DTEND:20260909T150000Z
RRULE:FREQ=DAILY;UNTIL=20260911T235959Z
UID:workshop-series@example.com
SUMMARY:Three Day Workshop
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 15)
        events = parse_ical_feed(ics_until, start_d, end_d, tz_str="-05:00")
        event_dates = [e["start"][:10] for e in events]
        self.assertEqual(event_dates, ["2026-09-09", "2026-09-10", "2026-09-11"])

    def test_rrule_count_active_and_exhausted(self):
        """COUNT must count occurrences sequentially from d_start and stop once reached."""
        # 1. COUNT terminates within window
        ics_count = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260909T140000Z
DTEND:20260909T150000Z
RRULE:FREQ=DAILY;COUNT=2
UID:two-day-sprint@example.com
SUMMARY:Two Day Sprint
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 15)
        events = parse_ical_feed(ics_count, start_d, end_d, tz_str="-05:00")
        event_dates = [e["start"][:10] for e in events]
        self.assertEqual(event_dates, ["2026-09-09", "2026-09-10"])

        # 2. COUNT was already exhausted before start_date
        ics_exhausted = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260901T140000Z
DTEND:20260901T150000Z
RRULE:FREQ=DAILY;COUNT=3
UID:past-sprint@example.com
SUMMARY:Past Sprint
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        events_past = parse_ical_feed(ics_exhausted, start_d, end_d, tz_str="-05:00")
        self.assertEqual(len(events_past), 0, "Exhausted COUNT series must produce 0 events in window")

    def test_exdate_filtering(self):
        """EXDATE must filter out excluded occurrence dates."""
        ics_exdate = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260909T140000Z
DTEND:20260909T150000Z
RRULE:FREQ=DAILY;UNTIL=20260913T235959Z
EXDATE:20260910T140000Z,20260911T140000Z
EXDATE;TZID=America/Chicago:20260912T090000
UID:daily-with-exceptions@example.com
SUMMARY:Daily Standup
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 15)
        events = parse_ical_feed(ics_exdate, start_d, end_d, tz_str="-05:00")
        event_dates = [e["start"][:10] for e in events]
        # Sept 10, 11, 12 are excluded, so only Sept 9 and Sept 13 remain
        self.assertEqual(event_dates, ["2026-09-09", "2026-09-13"])

    def test_rrule_until_intraday_cutoff(self):
        """Recurrence bounded by a DATE-TIME UNTIL must not generate instances after the cutoff time on the UNTIL date."""
        # Event is at 18:00 local (23:00 UTC). UNTIL is 07:00 local (12:00 UTC) on Sept 11.
        ics_intraday = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260909T230000Z
DTEND:20260910T000000Z
RRULE:FREQ=DAILY;UNTIL=20260911T120000Z
UID:intraday-cutoff@example.com
SUMMARY:Evening Lab Session
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 15)
        events = parse_ical_feed(ics_intraday, start_d, end_d, tz_str="-05:00")
        event_dates = [e["start"][:10] for e in events]
        # Sept 9 and 10 are generated; Sept 11 18:00 is after 07:00 UNTIL and must NOT be generated
        self.assertEqual(event_dates, ["2026-09-09", "2026-09-10"])

    def test_rrule_weekly_count_with_dtstart_not_in_byday(self):
        """DTSTART must always count as the first occurrence per RFC 5545 even if not in BYDAY."""
        # DTSTART is Tuesday Sept 8. BYDAY is MO,WE. COUNT=3.
        # Occurrences must be: Tue Sept 8 (DTSTART), Wed Sept 9 (BYDAY), Mon Sept 14 (BYDAY).
        ics_byday = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260908T180000Z
DTEND:20260908T190000Z
RRULE:FREQ=WEEKLY;BYDAY=MO,WE;COUNT=3
UID:tue-start-mowe@example.com
SUMMARY:Bi-Weekly Sprint
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 20)
        events = parse_ical_feed(ics_byday, start_d, end_d, tz_str="-05:00")
        event_dates = [e["start"][:10] for e in events]
        self.assertEqual(event_dates, ["2026-09-08", "2026-09-09", "2026-09-14"])

    def test_exdate_case_insensitivity_and_multi_value(self):
        """EXDATE parsing must handle lowercase property names, VALUE=DATE, and multiple lines."""
        ics_exdate_multi = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260909T180000Z
DTEND:20260909T190000Z
RRULE:FREQ=DAILY;COUNT=5
exdate:20260910T180000Z
EXDATE;VALUE=DATE:20260911,20260912
UID:case-and-value-date@example.com
SUMMARY:Flexible Standup
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
        start_d = date(2026, 9, 8)
        end_d = date(2026, 9, 15)
        events = parse_ical_feed(ics_exdate_multi, start_d, end_d, tz_str="-05:00")
        event_dates = [e["start"][:10] for e in events]
        # Sept 10 (via lowercase exdate), Sept 11 and Sept 12 (via VALUE=DATE) are excluded
        # Sept 9 and Sept 13 remain
        self.assertEqual(event_dates, ["2026-09-09", "2026-09-13"])


if __name__ == "__main__":
    unittest.main()
