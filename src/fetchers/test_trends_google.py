#!/usr/bin/env python3
"""Run: python src/fetchers/test_trends_google.py"""

from datetime import datetime, timezone

from trends_google import parse_export, parse_traffic

SAMPLE = (
    '"Trends","Search volume","Started","Ended","Trend breakdown","Explore link"\n'
    '"stock market","200K+","November 5, 2026 at 3:10:00 PM UTC",,"stock market,nasdaq","https://x"\n'
    '"lotus","500+","November 5, 2026 at 5:00:00 AM UTC","November 5, 2026 at 6:00:00 AM UTC","","https://x"\n'
)

rows = parse_export(SAMPLE)
assert [r["query"] for r in rows] == ["stock market", "lotus"]
assert rows[0]["volume"] == 200_000 and rows[1]["volume"] == 500
assert rows[0]["started"] == datetime(2026, 11, 5, 15, 10, tzinfo=timezone.utc)
assert rows[0]["related"] == ["stock market", "nasdaq"] and rows[1]["related"] == []
# An unreadable date costs that row its timestamp, not the whole list; rows sort by volume
rows = parse_export(SAMPLE.replace("November 5, 2026 at 5:00:00 AM UTC", "soon").replace('"500+"', '"900K+"'))
assert rows[0]["query"] == "lotus" and rows[0]["started"] is None
assert parse_traffic("1M+") == 1_000_000 and parse_traffic("") == 0
print("ok")
