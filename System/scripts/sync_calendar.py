#!/usr/bin/env python3
"""
Chrysalis Calendar Synchronizer (chrysalis-obsidian Bridge & Substrate Serializer)
Fetches dynamic external calendar events from chrysalis-obsidian / TaskNotes Local HTTP API (port 8080),
extracts locations, times, and recurrence metadata, and writes the 7-day snapshot
directly into Scheduling-Memory.md so autonomous orchestrators
and offline schedulers have instant zero-latency access.
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime, date, timedelta
from pathlib import Path

try:
    from .vault_paths import resolve_vault_root, vault_path, memory_path as resolve_memory_path
except ImportError:
    from vault_paths import resolve_vault_root, vault_path, memory_path as resolve_memory_path

DEFAULT_PORT = 8080
DEFAULT_HOST = "localhost"

def extract_timezone_from_memory(memory_content: str) -> str:
    """Extracts timezone_offset from frontmatter, defaulting to '-05:00'."""
    m = re.search(r'timezone_offset:\s*"([^"]+)"', memory_content)
    if m:
        return m.group(1)
    m = re.search(r'timezone_offset:\s*([^\s]+)', memory_content)
    if m:
        return m.group(1).strip('"\'')
    return "-05:00"

def get_chrysalis_events(start_date_str: str, end_date_str: str, port: int = DEFAULT_PORT, host: str = DEFAULT_HOST):
    """
    Queries chrysalis-obsidian / TaskNotes Local REST API for events between start_date_str and end_date_str.
    """
    try:
        start_bound = f"{start_date_str}T00:00:00"
        end_bound = f"{end_date_str}T23:59:59"
        
        url = f"http://{host}:{port}/api/calendars/events?start={urllib.parse.quote(start_bound)}&end={urllib.parse.quote(end_bound)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Chrysalis-Agent/1.0"})
        
        with urllib.request.urlopen(req, timeout=3.0) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("success") and "data" in payload:
                    data = payload["data"]
                    raw_events = data.get("events", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    return parse_events(raw_events)
    except Exception as e:
        return {"error": f"chrysalis-obsidian API unreachable on port {port}: {str(e)}", "events": []}
    
    return {"error": "Invalid response from chrysalis-obsidian API", "events": []}

get_tasknotes_events = get_chrysalis_events

def parse_events(raw_events: list):
    """
    Parses and normalizes raw event dicts from TaskNotes.
    """
    parsed = []
    for ev in raw_events:
        title = ev.get("title", "Untitled Event")
        start = ev.get("start", "")
        end = ev.get("end", "")
        all_day = ev.get("allDay", False)
        location = ev.get("location") or ""
        description = ev.get("description") or ""
        event_id = ev.get("id", "")
        recurring_id = ev.get("recurringEventId")
        
        has_phys_loc = bool(
            location and 
            not location.lower().startswith("http") and 
            "zoom" not in location.lower() and 
            "meet" not in location.lower() and 
            "teams" not in location.lower() and 
            "online" not in location.lower()
        )
        parsed.append({
            "id": event_id,
            "title": title,
            "start": start,
            "end": end,
            "all_day": all_day,
            "location": location,
            "has_physical_location": has_phys_loc,
            "is_recurring": bool(recurring_id),
            "description": description.strip() if description else ""
        })
            
    parsed.sort(key=lambda x: x.get("start", ""))
    return {"error": None, "events": parsed}

try:
    from fetch_ical import sync_ical
except ImportError:
    try:
        from System.scripts.fetch_ical import sync_ical
    except ImportError:
        sync_ical = None

def sync_to_memory(port: int = DEFAULT_PORT, memory_path: str = None, force_ical: bool = False):
    """
    Fetches the 7-day calendar window and serializes it into Scheduling-Memory.md.
    If chrysalis-obsidian on port 8080 is unreachable, automatically falls back to fetch_ical.
    """
    memory_path = str(resolve_memory_path(memory_path))
    p = Path(memory_path)
    if not p.exists():
        print(f"Memory file not found: {memory_path}")
        return False

    content = p.read_text(encoding="utf-8")
    is_ical_provider = 'provider: "ical_feed"' in content

    if force_ical or is_ical_provider:
        if sync_ical:
            return sync_ical(memory_path=memory_path)

    today = date.today()
    start_str = today.strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    
    res = get_chrysalis_events(start_str, end_str, port=port)
    if res.get("error"):
        print(f"Notice: {res['error']}")
        if sync_ical:
            print("[sync_calendar] chrysalis-obsidian port 8080 is offline. Seamlessly falling back to direct iCal feed...")
            return sync_ical(memory_path=memory_path)
        return False
    
    events = res.get("events", [])
    tz_offset = extract_timezone_from_memory(content)
    now_iso = datetime.now().strftime(f"%Y-%m-%dT%H:%M:%S{tz_offset}")
        
    lines = content.splitlines(keepends=True)
    out_lines = []
    in_cal_block = False
    
    for line in lines:
        if line.startswith("calendar_sync:"):
            in_cal_block = True
            out_lines.append("calendar_sync:\n")
            out_lines.append("  enabled: true\n")
            out_lines.append('  provider: "chrysalis_api"\n')
            out_lines.append(f"  port: {port}\n")
            out_lines.append(f'  last_sync: "{now_iso}"\n')
            out_lines.append(f'  horizon_start: "{start_str}"\n')
            out_lines.append(f'  horizon_end: "{end_str}"\n')
            if not events:
                out_lines.append("  cached_events: []\n")
            else:
                out_lines.append("  cached_events:\n")
                for ev in events:
                    out_lines.append(f'    - title: "{ev["title"]}"\n')
                    out_lines.append(f'      start: "{ev["start"]}"\n')
                    out_lines.append(f'      end: "{ev["end"]}"\n')
                    out_lines.append(f'      all_day: {str(ev["all_day"]).lower()}\n')
                    out_lines.append(f'      location: "{ev["location"]}"\n')
                    out_lines.append(f'      has_physical_location: {str(ev["has_physical_location"]).lower()}\n')
                    out_lines.append(f'      is_recurring: {str(ev["is_recurring"]).lower()}\n')
            continue
            
        if in_cal_block:
            if line.startswith("chronotype_telemetry:") or (line and not line.startswith(" ") and not line.startswith("\n") and not line.startswith("\r")):
                in_cal_block = False
                out_lines.append("\n" if not out_lines[-1].endswith("\n\n") else "")
                out_lines.append(line)
            continue
            
        out_lines.append(line)
        
    p.write_text("".join(out_lines), encoding="utf-8")
    print(f"Successfully synced {len(events)} calendar events to {memory_path}")
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Inspect or import calendar commitments")
    parser.add_argument("date", nargs="?", default=None)
    parser.add_argument("--vault", help="Selected vault root")
    parser.add_argument("--memory", help="Explicit memory file")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sync-to-memory", "--sync", dest="sync", action="store_true")
    parser.add_argument("--ical", action="store_true")
    parser.add_argument("--tomorrow", action="store_true")
    args = parser.parse_args()
    if args.sync or args.ical:
        memory = resolve_memory_path(args.memory, vault=args.vault)
        success = sync_to_memory(port=args.port, memory_path=str(memory), force_ical=args.ical)
        sys.exit(0 if success else 1)
    day = args.date or (date.today() + timedelta(days=int(args.tomorrow))).isoformat()
    result = get_chrysalis_events(day, day, port=args.port)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result.get("error") else 0)


if __name__ == "__main__":
    main()
