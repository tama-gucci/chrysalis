#!/usr/bin/env python3
"""
Chrysalis Inbound Calendar Ingestion Engine (Zero-Setup iCal Fetcher)
====================================================================
Metaphor & Architectural Overview:
----------------------------------
1. THE PORCH COURIER (urllib.request):
   Instead of requiring security badges and OAuth tokens, Google Calendar provides
   a private read-only URL (the "Secret address in iCal format"). This script acts
   as a personal courier, fetching the latest calendar schedule directly from
   that private web link.

2. UNFOLDING THE PAPER (RFC 5545 Text Unfolding):
   In iCalendar format, lines longer than 75 characters are broken into multiple
   lines with leading whitespace. Before reading the text, we "unfold" it back
   into complete sentences.

3. EVENT CAPSULES (BEGIN:VEVENT ... END:VEVENT):
   Each meeting, appointment, or class is wrapped in a VEVENT block. We extract
   the Title (SUMMARY), Times (DTSTART/DTEND), Location (LOCATION), and Notes (DESCRIPTION).

4. THE UNIVERSAL CLOCK TRANSLATOR (UTC -> Explicit Local Offset):
   Google stores times in Universal Time (UTC / "Z"). Chrysalis constitutional rules
   require explicit local wall-clock timestamps (e.g. "-05:00"). This script
   translates UTC times into your exact local time zone without any external libraries.

5. THE WEEKLY ECHO CHAMBER (Recurrence Expansion):
   Classes and weekly meetings usually started weeks or months ago and repeat
   using an RRULE. This engine calculates recurring occurrences for the upcoming
   7-day planning horizon.

6. THE KITCHEN REFRIGERATOR WHITEBOARD (System/Scheduling-Memory.md):
   Once events are parsed, they are neatly written into the cached_events list
   in Scheduling-Memory.md so the /plan engine can schedule focus sprints around them.
"""

import sys
import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

DEFAULT_HORIZON_DAYS = 7
WEEKDAY_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def parse_tz_offset(offset_str: str) -> timezone:
    """
    Translates a timezone string like '-05:00' or '+01:00' into a Python timezone object.
    Uses pure arithmetic so it works on any OS without external tzdata dependencies.
    """
    if not offset_str:
        return timezone.utc
    sign = -1 if offset_str.startswith("-") else 1
    clean = offset_str.lstrip("+-")
    parts = clean.split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return timezone(sign * timedelta(hours=h, minutes=m))


def parse_ical_dt(raw_line: str, tz_str: str, default_tz: timezone):
    """
    Parses an iCal date or datetime line into (date_obj, iso_string, is_all_day).
    Handles UTC ('Z'), local time, and date-only (all-day) formats.
    """
    if ":" not in raw_line:
        return None, None, False
        
    _, val = raw_line.split(":", 1)
    val = val.strip()
    
    # Check if all-day date (8 digits: YYYYMMDD)
    if len(val) == 8 and val.isdigit():
        d = date(int(val[:4]), int(val[4:6]), int(val[6:8]))
        return d, d.isoformat(), True
        
    # Date-time format: YYYYMMDDTHHMMSS[Z]
    clean_val = val.rstrip("Z")
    if "T" in clean_val:
        parts = clean_val.split("T")
        date_part, time_part = parts[0], parts[1]
        year, month, day = int(date_part[:4]), int(date_part[4:6]), int(date_part[6:8])
        hour = int(time_part[:2])
        minute = int(time_part[2:4]) if len(time_part) >= 4 else 0
        second = int(time_part[4:6]) if len(time_part) >= 6 else 0
        
        if val.endswith("Z"):
            dt_utc = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
            dt_local = dt_utc.astimezone(default_tz)
        else:
            # Already local wall-clock
            dt_local = datetime(year, month, day, hour, minute, second, tzinfo=default_tz)
            
        iso_str = dt_local.strftime("%Y-%m-%dT%H:%M:%S") + tz_str
        return dt_local.date(), iso_str, False
        
    return None, None, False


def parse_rrule(rrule_str: str) -> dict:
    """Parses an RRULE string into a dictionary (e.g. FREQ=WEEKLY;BYDAY=MO,WE)."""
    rule = {}
    for part in rrule_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            rule[k.upper()] = v.upper()
    return rule


def unfold_ical_text(raw_text: str) -> str:
    """
    Unfolds RFC 5545 lines: any newline followed immediately by a space or tab
    is joined back with the previous line.
    """
    return re.sub(r"(\r\n|\r|\n)[ \t]", "", raw_text)


def parse_vevent_blocks(unfolded_text: str) -> list:
    """Splits the iCalendar text into individual VEVENT blocks."""
    events = []
    current_block = []
    in_vevent = False
    
    for line in unfolded_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "BEGIN:VEVENT":
            in_vevent = True
            current_block = []
        elif line == "END:VEVENT":
            if in_vevent:
                events.append(current_block)
            in_vevent = False
        elif in_vevent:
            current_block.append(line)
            
    return events


def parse_ical_feed(ics_text: str, start_date: date, end_date: date, tz_str: str = "-05:00") -> list:
    """
    Parses raw iCal text and returns normalized event dictionaries falling
    between start_date and end_date. Expands basic daily and weekly recurrences.
    """
    default_tz = parse_tz_offset(tz_str)
    raw_blocks = parse_vevent_blocks(unfold_ical_text(ics_text))
    
    parsed_events = []
    
    for block in raw_blocks:
        ev_dict = {"exdates": []}
        for line in block:
            line_upper = line.upper()
            if line_upper.startswith("SUMMARY"):
                ev_dict["summary"] = line.split(":", 1)[1].replace(r"\,", ",").replace(r"\;", ";").replace(r"\\", "\\")
            elif line_upper.startswith("LOCATION"):
                ev_dict["location"] = line.split(":", 1)[1].replace(r"\,", ",").replace(r"\;", ";").replace(r"\\", "\\")
            elif line_upper.startswith("DESCRIPTION"):
                ev_dict["description"] = line.split(":", 1)[1].replace(r"\,", ",").replace(r"\;", ";").replace(r"\\", "\\")
            elif line_upper.startswith("UID"):
                ev_dict["uid"] = line.split(":", 1)[1]
            elif line_upper.startswith("STATUS"):
                ev_dict["status"] = line.split(":", 1)[1].upper()
            elif line_upper.startswith("DTSTART"):
                ev_dict["dtstart_line"] = line
            elif line_upper.startswith("DTEND"):
                ev_dict["dtend_line"] = line
            elif line_upper.startswith("RRULE"):
                ev_dict["rrule"] = line.split(":", 1)[1]
            elif line_upper.startswith("EXDATE"):
                ev_dict["exdates"].append(line.split(":", 1)[1])
                
        # Skip cancelled events
        if ev_dict.get("status") == "CANCELLED":
            continue
            
        dtstart_line = ev_dict.get("dtstart_line")
        if not dtstart_line:
            continue
            
        d_start, iso_start, all_day = parse_ical_dt(dtstart_line, tz_str, default_tz)
        if not d_start:
            continue
            
        if "dtend_line" in ev_dict:
            d_end, iso_end, _ = parse_ical_dt(ev_dict["dtend_line"], tz_str, default_tz)
        else:
            d_end, iso_end = d_start, iso_start
            
        duration = timedelta(hours=1)
        if not all_day and iso_start and iso_end:
            try:
                t0 = datetime.fromisoformat(iso_start)
                t1 = datetime.fromisoformat(iso_end)
                duration = max(t1 - t0, timedelta(minutes=15))
            except Exception:
                pass
                
        title = ev_dict.get("summary", "Untitled Event")
        location = ev_dict.get("location", "")
        uid = ev_dict.get("uid", "")
        rrule_str = ev_dict.get("rrule")
        
        has_phys_loc = bool(
            location and 
            not location.lower().startswith("http") and 
            "zoom" not in location.lower() and 
            "meet" not in location.lower() and 
            "teams" not in location.lower() and 
            "online" not in location.lower()
        )

        exdate_dates = set()
        for exdate_str in ev_dict.get("exdates", []):
            for part in exdate_str.split(","):
                part = part.strip()
                if part:
                    d_ex, _, _ = parse_ical_dt(":" + part, tz_str, default_tz)
                    if d_ex:
                        exdate_dates.add(d_ex)
        
        # Handle recurring events
        if rrule_str:
            rule = parse_rrule(rrule_str)
            freq = rule.get("FREQ")
            bydays_raw = rule.get("BYDAY", "")
            bydays = [WEEKDAY_MAP[d] for d in bydays_raw.split(",") if d in WEEKDAY_MAP]

            until_str = rule.get("UNTIL")
            d_until = None
            dt_until = None
            until_all_day = False
            if until_str:
                d_until, iso_until, until_all_day = parse_ical_dt(":" + until_str, tz_str, default_tz)
                if d_until and d_until < start_date:
                    continue
                if iso_until and not until_all_day:
                    try:
                        dt_until = datetime.fromisoformat(iso_until)
                    except Exception:
                        pass

            count_str = rule.get("COUNT")
            max_count = int(count_str) if count_str and count_str.isdigit() else None
            if max_count is not None and max_count <= 0:
                continue

            curr = d_start if max_count else max(start_date, d_start)
            occ_count = 0
            while curr <= end_date:
                if d_until and curr > d_until:
                    break
                matches = False
                if freq == "DAILY":
                    matches = True
                elif freq == "WEEKLY":
                    if curr == d_start:
                        matches = True
                    elif bydays:
                        matches = curr.weekday() in bydays
                    else:
                        matches = (curr.weekday() == d_start.weekday())
                        
                if matches:
                    if not all_day and dt_until:
                        t0_time = datetime.fromisoformat(iso_start).time()
                        occ_dt = datetime.combine(curr, t0_time, tzinfo=default_tz)
                        if occ_dt > dt_until:
                            break

                    if max_count:
                        occ_count += 1
                        if occ_count > max_count:
                            break
                    if curr >= start_date and curr not in exdate_dates:
                        if all_day:
                            occ_start = curr.isoformat()
                            occ_end = (curr + timedelta(days=1)).isoformat()
                        else:
                            t0_time = datetime.fromisoformat(iso_start).time()
                            occ_dt = datetime.combine(curr, t0_time, tzinfo=default_tz)
                            occ_start = occ_dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_str
                            occ_end = (occ_dt + duration).strftime("%Y-%m-%dT%H:%M:%S") + tz_str
                            
                        parsed_events.append({
                            "id": f"{uid}_{curr.strftime('%Y%m%d')}",
                            "title": title,
                            "start": occ_start,
                            "end": occ_end,
                            "all_day": all_day,
                            "location": location,
                            "has_physical_location": has_phys_loc,
                            "is_recurring": True
                        })
                    if max_count and occ_count >= max_count:
                        break
                curr += timedelta(days=1)
        else:
            # Single non-recurring event
            if start_date <= d_start <= end_date and d_start not in exdate_dates:
                parsed_events.append({
                    "id": uid,
                    "title": title,
                    "start": iso_start,
                    "end": iso_end,
                    "all_day": all_day,
                    "location": location,
                    "has_physical_location": has_phys_loc,
                    "is_recurring": False
                })
                
    parsed_events.sort(key=lambda x: x.get("start", ""))
    return parsed_events


def fetch_ical_url(url: str) -> str:
    """Downloads the iCalendar feed over HTTP/HTTPS with proper timeout and headers."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Chrysalis-Calendar-Sync/1.0 (Python urllib)"}
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP error {resp.status} fetching calendar feed")
        return resp.read().decode("utf-8", errors="replace")


def extract_timezone_from_memory(memory_content: str) -> str:
    """Extracts timezone_offset from frontmatter, defaulting to '-05:00'."""
    m = re.search(r'timezone_offset:\s*"([^"]+)"', memory_content)
    if m:
        return m.group(1)
    m = re.search(r'timezone_offset:\s*([^\s]+)', memory_content)
    if m:
        return m.group(1).strip('"\'')
    return "-05:00"


def extract_ical_url_from_memory(memory_content: str) -> str:
    """Extracts ical_url from Scheduling-Memory.md if present."""
    m = re.search(r'ical_url:\s*"([^"]+)"', memory_content)
    if m:
        return m.group(1)
    m = re.search(r'ical_url:\s*([^\s]+)', memory_content)
    if m:
        val = m.group(1).strip('"\'')
        return val if val != '""' and val != "null" else ""
    return ""


def serialize_calendar_block(events: list, ical_url: str, now_iso: str, start_str: str, end_str: str) -> list:
    """Generates the clean YAML lines for the calendar_sync block."""
    lines = [
        "calendar_sync:\n",
        "  enabled: true\n",
        '  provider: "ical_feed"\n',
        f'  ical_url: "{ical_url}"\n',
        f'  last_sync: "{now_iso}"\n',
        f'  horizon_start: "{start_str}"\n',
        f'  horizon_end: "{end_str}"\n'
    ]
    if not events:
        lines.append("  cached_events: []\n")
    else:
        lines.append("  cached_events:\n")
        for ev in events:
            lines.append(f'    - title: "{ev["title"]}"\n')
            lines.append(f'      start: "{ev["start"]}"\n')
            lines.append(f'      end: "{ev["end"]}"\n')
            lines.append(f'      all_day: {str(ev["all_day"]).lower()}\n')
            lines.append(f'      location: "{ev["location"]}"\n')
            lines.append(f'      has_physical_location: {str(ev["has_physical_location"]).lower()}\n')
            lines.append(f'      is_recurring: {str(ev["is_recurring"]).lower()}\n')
    return lines


def update_scheduling_memory(memory_path: str, events: list, ical_url: str, tz_str: str, start_str: str, end_str: str):
    """
    Safely writes the calendar_sync block into Scheduling-Memory.md.
    If calendar_sync exists, it replaces the block.
    If calendar_sync does NOT exist, it inserts it before chronotype_telemetry or closing frontmatter.
    """
    p = Path(memory_path)
    if not p.exists():
        raise FileNotFoundError(f"Memory file not found: {memory_path}")
        
    content = p.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    
    now_dt = datetime.now(parse_tz_offset(tz_str))
    now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_str
    
    cal_block_lines = serialize_calendar_block(events, ical_url, now_iso, start_str, end_str)
    
    out_lines = []
    in_cal_block = False
    cal_block_replaced = False
    
    for line in lines:
        if line.startswith("calendar_sync:"):
            in_cal_block = True
            cal_block_replaced = True
            out_lines.extend(cal_block_lines)
            continue
            
        if in_cal_block:
            # Check if leaving calendar_sync block
            if line.startswith("chronotype_telemetry:") or (line and not line.startswith(" ") and not line.startswith("\n") and not line.startswith("\r")):
                in_cal_block = False
                out_lines.append("\n" if not out_lines[-1].endswith("\n\n") else "")
                out_lines.append(line)
            continue
            
        # If calendar_sync was never found and we reach chronotype_telemetry, insert it before!
        if not cal_block_replaced and line.startswith("chronotype_telemetry:"):
            out_lines.extend(cal_block_lines)
            out_lines.append("\n")
            cal_block_replaced = True
            
        out_lines.append(line)
        
    # If still not inserted (e.g. no chronotype_telemetry found), insert before the second '---'
    if not cal_block_replaced:
        final_lines = []
        dash_count = 0
        for line in out_lines:
            if line.strip() == "---":
                dash_count += 1
                if dash_count == 2:
                    final_lines.extend(cal_block_lines)
                    final_lines.append("\n")
            final_lines.append(line)
        out_lines = final_lines
        
    p.write_text("".join(out_lines), encoding="utf-8")
    return True


def sync_ical(ical_url: str = None, memory_path: str = None, horizon_days: int = DEFAULT_HORIZON_DAYS):
    """Main orchestration function to fetch and sync iCal events to memory."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    if not memory_path:
        memory_path = os.environ.get("CHRYSALIS_MEMORY_PATH")
        if not memory_path:
            vault_base = os.environ.get("CHRYSALIS_VAULT_PATH")
            candidates = []
            if vault_base:
                candidates.extend([
                    Path(vault_base) / "chrysalis" / "System" / "Scheduling-Memory.md",
                    Path(vault_base) / "System" / "Scheduling-Memory.md",
                ])
            candidates.extend([
                repo_root.parent / "chrysalis" / "System" / "Scheduling-Memory.md",
                repo_root.parent / "chrysalis" / "chrysalis" / "System" / "Scheduling-Memory.md",
                Path(__file__).resolve().parent.parent / "Scheduling-Memory.md",
                repo_root / "chrysalis" / "System" / "Scheduling-Memory.md",
                repo_root / "System" / "Scheduling-Memory.md",
            ])
            for candidate in candidates:
                if candidate.exists():
                    memory_path = str(candidate)
                    break
            if not memory_path:
                memory_path = str(candidates[0])
                
    p = Path(memory_path)
    if not p.exists():
        print(f"[fetch_ical] Error: Memory file not found at {memory_path}")
        return False
        
    content = p.read_text(encoding="utf-8")
    tz_str = extract_timezone_from_memory(content)
    
    if not ical_url:
        ical_url = os.environ.get("CHRYSALIS_ICAL_URL") or extract_ical_url_from_memory(content)
        
    if not ical_url:
        print("[fetch_ical] Notice: No ical_url found in Scheduling-Memory.md or CHRYSALIS_ICAL_URL environment variable.")
        print("[fetch_ical] To connect: paste your Google Calendar Secret iCal URL into Scheduling-Memory.md under calendar_sync.ical_url.")
        return False
        
    today = date.today()
    end_date = today + timedelta(days=horizon_days)
    start_str = today.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"[fetch_ical] Fetching iCal feed from: {ical_url[:40]}... (Horizon: {start_str} to {end_str})")
    try:
        raw_ics = fetch_ical_url(ical_url)
    except Exception as e:
        print(f"[fetch_ical] Error fetching calendar URL: {e}")
        return False
        
    events = parse_ical_feed(raw_ics, today, end_date, tz_str=tz_str)
    print(f"[fetch_ical] Parsed {len(events)} upcoming events.")
    
    update_scheduling_memory(memory_path, events, ical_url, tz_str, start_str, end_str)
    print(f"[fetch_ical] Successfully synchronized {len(events)} events into {memory_path}")
    return True


def main():
    """Command-line entrypoint for testing and manual sync."""
    if "--help" in sys.argv:
        print("Usage:")
        print("  python fetch_ical.py                     # Syncs using URL from Scheduling-Memory.md")
        print("  python fetch_ical.py --url <secret_url>  # Syncs using specified iCal URL")
        print("  python fetch_ical.py --print             # Prints parsed events as JSON")
        sys.exit(0)
        
    target_url = None
    for i, arg in enumerate(sys.argv):
        if arg == "--url" and i + 1 < len(sys.argv):
            target_url = sys.argv[i + 1]
            
    success = sync_ical(ical_url=target_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
