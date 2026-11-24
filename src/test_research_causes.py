from deliver import add_tape_notes, apply_research, market_context, unexplained_indices

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

    spikes = [{"url": u, "cause_unclear": True, "tape": "96% in one bar."} for u in "abc"]
    spikes += [{"url": "d", "tape": "96% in one bar."}, {"url": "e", "cause_unclear": True, "tape": ""}]
    found = [{"index": 0, "description": "Bond ETF.", "cause_found": False, "url": "https://x.com/fund"},
             {"index": 1, "description": "NVDA ETF rose on Huang.", "cause_found": True, "url": None}]
    descs = apply_research(spikes, ["A", "B", "Unclear.", "D", "E"], found, resolves=lambda u: True)
    assert spikes[0]["url"] == "a"  # no cause: not linked to a background page
    # index 2 was never researched (failed call), so it gets the tape too
    assert add_tape_notes(spikes, descs) == ["Bond ETF. 96% in one bar.", "NVDA ETF rose on Huang.",
                                             "Unclear. 96% in one bar.", "D", "E No cause was reported."]
    print("ok")
