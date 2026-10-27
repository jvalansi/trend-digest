from datetime import date, timedelta

from citation_velocity import record_gains

if __name__ == "__main__":
    d = lambda n: (date(2026, 10, 27) - timedelta(days=n)).isoformat()
    history = {"src": {
        "old": {d(20): 1, d(9): 50, d(7): 60, d(3): 70},  # baseline = day -7
        "new": {d(4): 5},                                 # baseline = oldest
        "young": {d(2): 5},                               # under MIN_DAYS
    }}
    gains = record_gains("src", {"old": 100, "new": 11, "young": 9, "first": 40}, history, date(2026, 10, 27))
    # old: +40 over 7 days; new: +6 over 4 days → 10.5 per week; young/first: too little history
    assert gains == {"old": 40, "new": 10.5, "young": 0, "first": 0}, gains
    assert d(20) not in history["src"]["old"]  # pruned past KEEP_DAYS
    print("ok")
