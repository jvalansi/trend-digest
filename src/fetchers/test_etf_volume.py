from etf_volume import fresh_quotes

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
    print("ok")
