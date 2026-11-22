from deliver import apply_research, market_context, unexplained_indices

if __name__ == "__main__":
    flags = [{"index": 0, "unexplained": True}, {"index": 1, "unexplained": False},
             {"index": 2.0, "unexplained": True}, {"index": 7, "unexplained": True}, "junk"]
    assert unexplained_indices(flags, 3) == {0}

    items = [{"url": "a", "cause_unclear": True}, {"url": "b"}, {"url": "c", "cause_unclear": True},
             {"url": "d", "cause_unclear": True}]
    descs = ["unclear a", "fine b", "unclear c", "unclear d"]
    findings = [
        {"index": 0, "description": "A fell on CMS audits.", "url": "https://x.com/a"},
        {"index": 1, "description": "overwrite me?", "url": "https://x.com/b"},  # not flagged: ignored
        {"index": 2, "description": "No cause was reported.", "url": None},
        {"index": 3, "description": "D rose on a deal.", "url": "https://x.com/dead"},  # dead link: text only
        {"index": 9, "description": "out of range"}, "junk", ["nested"],
    ]
    out = apply_research(items, descs, findings, resolves=lambda u: u != "https://x.com/dead")
    assert out == ["A fell on CMS audits.", "fine b", "No cause was reported.", "D rose on a deal."]
    assert [i["url"] for i in items] == ["https://x.com/a", "b", "c", "d"]
    assert apply_research(items, descs, {"not": "a list"}) == descs

    close = {"source": "FMP Market", "title": "Market close 2026-11-20: S&P 500 -3.7%",
             "summary": "S&P 500 -3.7%; 2Y 4.63% (-13bp)"}
    assert market_context([{"source": "FMP Movers", "title": "GS -6.7%"}, close]) == close["summary"]
    assert market_context([{"source": "FMP Market", "title": "Coming up: CPI"}]) == ""
    print("ok")
