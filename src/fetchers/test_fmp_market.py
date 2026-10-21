from datetime import date, datetime, timezone

from fmp_market import daily_vol, rank_movers, short_name, upcoming_session, useful_news

if __name__ == "__main__":
    # alternating ±1% days → ~1% daily vol
    vol = daily_vol([100 * (1.01 if i % 2 else 1.0) for i in range(41)])
    assert 0.009 < vol < 0.012, vol
    assert daily_vol([100, 101]) is None

    rows = [{"symbol": "BIG", "changesPercentage": -6.0}, {"symbol": "LOWVOL", "changesPercentage": 3.0},
            {"symbol": "NOISY", "changesPercentage": 9.0}, {"symbol": "NOVOL", "changesPercentage": 20.0}]
    vols = {"BIG": 0.02, "LOWVOL": 0.01, "NOISY": 0.06}
    ranked = rank_movers(rows, vols, min_z=2)
    assert [(q["symbol"], q["z"]) for q in ranked] == [("BIG", -3.0), ("LOWVOL", 3.0)], ranked

    news = [{"site": "defenseworld.net", "title": "x"}, {"site": "reuters.com", "title": "Acme Fund Sells 1,200 Shares of FOO"},
            {"site": "reuters.com", "title": "FOO cuts guidance"}]
    assert [n["title"] for n in useful_news(news)] == ["FOO cuts guidance"]
    assert short_name("Kinder Morgan, Inc.") == "Kinder Morgan"
    assert short_name("Enterprise Products Partners L.P.") == "Enterprise Products Partners"
    assert short_name("Inc") == "Inc"
    utc = lambda *a: datetime(*a, tzinfo=timezone.utc)
    assert upcoming_session(utc(2026, 10, 21, 12, 50)) == date(2026, 10, 21)  # Wed pre-open → same day
    assert upcoming_session(utc(2026, 10, 21, 20, 0)) == date(2026, 10, 22)   # EDT close (16:00 ET) → Thu
    assert upcoming_session(utc(2026, 12, 2, 20, 30)) == date(2026, 12, 2)    # EST, 15:30 ET still open
    assert upcoming_session(utc(2026, 10, 23, 21, 30)) == date(2026, 10, 26)  # Fri after close → Mon
    assert upcoming_session(utc(2026, 10, 24, 12, 50)) == date(2026, 10, 26)  # Sat → Mon
    print("ok")
