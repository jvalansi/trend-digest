import io
import urllib.error

import semantic_scholar as s2

if __name__ == "__main__":
    calls = []
    def always_429(req, timeout):
        calls.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO())
    s2.urllib.request.urlopen = always_429
    s2.time.sleep = lambda _: None
    try:
        s2.fetch_papers(365, 20, "science")
        raise AssertionError("expected all-failed queries to raise")
    except RuntimeError as e:
        assert "all 6 queries failed" in str(e)
    assert len(calls) == 6 * s2.MAX_ATTEMPTS  # every query retried up to the cap, no more
    print("ok")
