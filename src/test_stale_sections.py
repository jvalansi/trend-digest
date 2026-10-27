from datetime import datetime, timedelta, timezone

from deliver import seen_days, stale_footer, stale_sections, update_seen

if __name__ == "__main__":
    today = datetime.now(timezone.utc).date()
    yday = (today - timedelta(days=1)).isoformat()
    entry = lambda n: {"first_seen": "2026-01-01", "last_seen": yday, "count": n, "days": n}
    seen = {"a": entry(9), "b": entry(4), "c": entry(9),
            # legacy: 3 modes x 2 days = count 6, but only 2 distinct days
            "legacy": {"first_seen": (today - timedelta(days=2)).isoformat(), "last_seen": yday, "count": 6}}
    assert seen_days(seen["legacy"]) == 2
    items = [{"url": u} for u in ("a", "b", "c", "new", "legacy")]
    update_seen(items, seen)
    update_seen(items, seen)  # second run same day: count moves, days don't
    assert seen["a"]["days"] == 10 and seen["a"]["count"] == 11
    assert seen["b"]["days"] == 5 and seen["new"]["days"] == 1 and seen["legacy"]["days"] == 3

    groups = {"Papers": items[:3], "News": items[3:], "Solo": items[:1]}
    assert stale_sections(groups, seen) == [("Papers", 1.0)]
    assert "Papers 100%" in stale_footer(stale_sections(groups, seen))
    assert stale_footer([]) == ""
    print("ok")
