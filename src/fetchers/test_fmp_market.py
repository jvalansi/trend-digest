from fmp_market import daily_vol, rank_movers, useful_news

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
    print("ok")
