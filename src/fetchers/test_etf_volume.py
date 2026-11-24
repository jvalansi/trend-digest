from etf_volume import baseline_volume, fresh_quotes, rescore, tape_note

if __name__ == "__main__":
    day = 86400
    now = 1_800_000_000
    quotes = [
        {"symbol": "SPY", "timestamp": now},
        {"symbol": "FRI", "timestamp": now - 3 * day},
        {"symbol": "TVIX", "timestamp": now - 2000 * day},
        {"symbol": "NOTS"},
    ]
    assert [q["symbol"] for q in fresh_quotes(quotes)] == ["SPY", "FRI"]
    assert fresh_quotes([]) == []

    # LITX: FMP's quote said avg 27,700, its own history says ~3M a day
    hist = [{"date": "2026-11-20", "volume": 3_200_000}] + [
        {"date": f"2026-10-{d:02d}", "volume": 3_000_000} for d in range(30, 0, -1)]
    assert baseline_volume(hist, "2026-11-20") == 3_000_000  # the session itself is excluded
    assert baseline_volume(hist[:4], "2026-11-20") is None   # too little history to judge

    cands = [{"ticker": t, "price": 20.0, "today_volume": 3_200_000, "avg_volume": 27_700, "ratio": 115.5}
             for t in ("LITX", "THIN", "NEW")]
    bases = {"LITX": 3_000_000, "THIN": 2_000_000, "NEW": None}
    out = rescore(cands, lambda c: bases[c["ticker"]])
    assert [(r["ticker"], r["avg_volume"], r["ratio"]) for r in out] == [("LITX", 3_000_000, 1.07)]

    def bars(*vols, start=40):
        return [{"date": f"2026-11-23 09:{start + i}:00", "volume": v} for i, v in enumerate(vols)]
    assert tape_note(bars(1000, 20, 20), "2026-11-23", 1040).startswith("96% of the day's volume came in one")
    assert tape_note(bars(1000, 20, 20, start=30), "2026-11-23", 1040) == ""  # opening bar
    assert tape_note(bars(20, 20, 1000), "2026-11-23", 1040) == ""  # closing bar
    assert tape_note(bars(5, 4), "2026-11-23", 100).startswith("Only 9%")
    assert tape_note(bars(700, 111), "2026-11-23", 100) == ""  # bars contradict the daily volume
    assert tape_note(bars(*[10] * 10), "2026-11-23", 100) == ""  # spread through the day
    assert tape_note(bars(100), "2026-11-20", 100) == ""  # no bars for the session
    print("ok")
