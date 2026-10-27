from datetime import datetime, timezone

from polymarket import volume_surge

if __name__ == "__main__":
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    ev = lambda **kw: {"createdAt": "2026-09-01T00:00:00Z", "volume24hr": 600_000, "volume1wk": 1_200_000, **kw}
    assert volume_surge(ev(), now) == 6.0                                   # 600k vs 100k/day before
    assert volume_surge(ev(createdAt="2026-10-25T00:00:00Z"), now) is None  # too new
    assert volume_surge(ev(tags=[{"slug": "games"}]), now) is None          # single match
    assert volume_surge(ev(tags=[{"slug": "recurring"}]), now) is None      # rolling series
    assert volume_surge(ev(markets=[{"endDate": f"2026-11-{d:02d}"} for d in range(1, 11)]), now) is None  # date ladder
    assert volume_surge(ev(volume1wk=600_100), now) is None                 # dormant before today
    assert volume_surge(ev(volume24hr=50_000, volume1wk=100_000), now) is None  # too thin
    print("ok")
