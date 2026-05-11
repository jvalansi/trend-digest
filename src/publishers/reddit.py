"""Submit a link post to one or more subreddits via Reddit OAuth API."""

import json
import urllib.parse
import urllib.request


def _get_access_token(client_id: str, client_secret: str, username: str, password: str) -> str:
    creds = urllib.parse.urlencode({"grant_type": "password", "username": username, "password": password}).encode()
    import base64
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=creds,
        headers={
            "Authorization": f"Basic {auth}",
            "User-Agent": "trend-digest/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["access_token"]


def post(
    title: str,
    url: str,
    subreddits: list[str],
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> list[dict]:
    """Submit a link post to each subreddit. Returns list of API responses."""
    token = _get_access_token(client_id, client_secret, username, password)
    results = []
    for subreddit in subreddits:
        body = urllib.parse.urlencode({
            "kind": "link",
            "sr": subreddit,
            "title": title,
            "url": url,
            "resubmit": True,
        }).encode()
        req = urllib.request.Request(
            "https://oauth.reddit.com/api/submit",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "trend-digest/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            results.append(json.loads(resp.read()))
    return results
