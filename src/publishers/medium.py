"""Publish a digest post to Medium."""

import json
import urllib.request


import os

_HEADERS = {"User-Agent": "trend-digest/1.0"}


def _get_user_id(token: str) -> str:
    if uid := os.environ.get("MEDIUM_USER_ID"):
        return uid
    req = urllib.request.Request(
        "https://api.medium.com/v1/me",
        headers={**_HEADERS, "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["data"]["id"]


def publish(title: str, content_md: str, token: str, tags: list[str] | None = None) -> str:
    """Publish markdown content as a Medium post. Returns the post URL."""
    user_id = _get_user_id(token)
    body = {
        "title": title,
        "contentFormat": "markdown",
        "content": content_md,
        "publishStatus": "unlisted",  # Medium API no longer allows "public" via integration tokens
        "tags": tags or ["technology", "ai", "machine-learning", "startups", "news"],
    }
    req = urllib.request.Request(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        data=json.dumps(body).encode(),
        headers={**_HEADERS, "Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    return result["data"]["url"]
