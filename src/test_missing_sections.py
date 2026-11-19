from aggregate import missing_sections, rss_feed_names
from deliver import missing_footer

if __name__ == "__main__":
    pools = {"Altmetric": [{"url": "a"}], "OpenAlex Early Signal": [], "Reddit Science": []}
    missing = missing_sections(pools, failed={"OpenAlex Early Signal"})
    assert missing == [{"section": "OpenAlex Early Signal", "reason": "fetcher failed"},
                       {"section": "Reddit Science", "reason": "no items"}]
    assert "Scientific American" in rss_feed_names(["python", "src/fetchers/rss.py", "--category", "science"])
    assert "The Verge" not in rss_feed_names(["python", "src/fetchers/rss.py", "--category", "science"])
    footer = missing_footer(missing, ["Scientific American"])
    assert footer == ("ℹ Missing today: OpenAlex Early Signal (fetcher failed), Reddit Science (no items); "
                      "RSS feeds with no items: Scientific American")
    assert missing_footer([], []) == ""
    print("ok")
