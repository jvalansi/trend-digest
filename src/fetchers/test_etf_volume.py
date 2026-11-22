from etf_volume import baseline_volume, fresh_quotes, rescore

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

    cands = [{"ticker": t, "today_volume": 3_200_000, "avg_volume": 27_700, "ratio": 115.5}
             for t in ("LITX", "THIN", "NEW")]
    bases = {"LITX": 3_000_000, "THIN": 5_000, "NEW": None}
    out = rescore(cands, lambda c: bases[c["ticker"]])
    assert [(r["ticker"], r["avg_volume"], r["ratio"]) for r in out] == [("LITX", 3_000_000, 1.07)]
    print("ok")
