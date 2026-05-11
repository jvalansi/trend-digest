"""Post a link card to Bluesky."""

import json
import urllib.request
from datetime import datetime, timezone

_API = "https://bsky.social/xrpc"


def _create_session(handle: str, password: str) -> dict:
    body = {"identifier": handle, "password": password}
    req = urllib.request.Request(
        f"{_API}/com.atproto.server.createSession",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def post(text: str, url: str, title: str, description: str, handle: str, password: str) -> dict:
    """Post text + link card to Bluesky. Returns the createRecord response."""
    session = _create_session(handle, password)
    token = session["accessJwt"]
    did = session["did"]

    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "embed": {
            "$type": "app.bsky.embed.external",
            "external": {"uri": url, "title": title, "description": description},
        },
    }
    body = {"repo": did, "collection": "app.bsky.feed.post", "record": record}
    req = urllib.request.Request(
        f"{_API}/com.atproto.repo.createRecord",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())
