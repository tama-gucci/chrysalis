import { Temporal } from "@js-temporal/polyfill";

export function zoneName(zone: string): string {
  if (typeof zone !== "string" || !zone || /^[+-]/.test(zone))
    throw new Error("Use a named IANA timezone");
  const resolved = new Intl.DateTimeFormat("en", {
    timeZone: zone,
  }).resolvedOptions().timeZone;
  Temporal.Now.instant().toZonedDateTimeISO(resolved);
  return resolved;
}
export function instant(value: string) {
  return Temporal.Instant.from(value);
}
export function stamp(value: string, zone: string, strict = true) {
  zone = zoneName(zone);
  if (typeof value !== "string" || !/T/.test(value))
    throw new Error("Use a datetime");
  if (!/(?:Z|[+-]\d\d:\d\d)$/.test(value)) {
    if (strict) throw new Error("Use an explicit local timestamp");
    const plain = Temporal.PlainDateTime.from(value);
    return plain.toZonedDateTime(zone, { disambiguation: "reject" });
  }
  if (strict && value.endsWith("Z"))
    throw new Error("Use an explicit offset instead of Z");
  const zdt = instant(value).toZonedDateTimeISO(zone);
  if (strict && zdt.offset !== value.slice(-6))
    throw new Error("Timestamp offset does not match the configured timezone");
  return zdt;
}
export function serialize(
  value: string | Temporal.Instant | Temporal.ZonedDateTime,
  zone: string,
): string {
  const result =
    typeof value === "string"
      ? instant(value).toZonedDateTimeISO(zoneName(zone))
      : "timeZoneId" in value
        ? value.toInstant().toZonedDateTimeISO(zoneName(zone))
        : value.toZonedDateTimeISO(zoneName(zone));
  return result.toString({
    timeZoneName: "never",
    calendarName: "never",
    fractionalSecondDigits: 0,
  });
}
export const nowStamp = (zone: string, now?: string) =>
  serialize(now ?? Temporal.Now.instant().toString(), zone);
export const dateOnly = (date: string) => Temporal.PlainDate.from(date);
export function wallTime(
  value: string,
  zone: string,
  choice?: "earlier" | "later",
) {
  const plain = Temporal.PlainDateTime.from(value);
  const earlier = plain.toZonedDateTime(zoneName(zone), {
    disambiguation: "earlier",
  });
  const later = plain.toZonedDateTime(zoneName(zone), {
    disambiguation: "later",
  });
  if (
    !earlier.toPlainDateTime().equals(plain) ||
    !later.toPlainDateTime().equals(plain)
  )
    throw new Error("Nonexistent local wall time");
  if (earlier.epochMilliseconds !== later.epochMilliseconds && !choice)
    throw new Error("Ambiguous local time: choose earlier or later");
  return choice === "later" ? later : earlier;
}
export function businessDate(start: string, days: number) {
  if (!Number.isInteger(days) || days < 3 || days > 5)
    throw new Error("Institutional verification requires 3–5 business days");
  let current = dateOnly(start);
  for (let n = 0; n < days; n++) {
    do {
      current = current.add({ days: 1 });
    } while (current.dayOfWeek >= 6);
  }
  return current.toString();
}

/** TaskNotes accepts single-digit hours and an end-of-day midnight boundary. */
export function nativeTimeblockInterval(
  date: string,
  start: string,
  end: string,
  zone: string,
): [number, number] {
  const minutes = (value: string, isEnd = false) => {
    if (isEnd && value === "24:00") return 1440;
    const match = /^([01]?[0-9]|2[0-3]):([0-5][0-9])$/.exec(value);
    if (!match) throw new Error("Invalid native timeblock clock");
    return Number(match[1]) * 60 + Number(match[2]);
  };
  const a = minutes(start),
    b = end === "00:00" && a > 0 ? 1440 : minutes(end, true);
  if (b <= a)
    throw new Error(
      "Invalid native timeblock interval; review it before planning",
    );
  const clock = (n: number) =>
    String(Math.floor(n / 60)).padStart(2, "0") +
    ":" +
    String(n % 60).padStart(2, "0");
  return [
    wallTime(date + "T" + clock(a), zone).epochMilliseconds,
    wallTime(
      (b === 1440 ? dateOnly(date).add({ days: 1 }).toString() : date) +
        "T" +
        clock(b % 1440),
      zone,
    ).epochMilliseconds,
  ];
}
