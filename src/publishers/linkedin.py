"""Share an article link on LinkedIn via UGC Posts API."""

import json
import urllib.request


def post(text: str, url: str, title: str, token: str, person_urn: str) -> dict:
    """Share a link post on LinkedIn. Returns the API response."""
    body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "ARTICLE",
                "media": [{"status": "READY", "originalUrl": url, "title": {"text": title}}],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/ugcPosts",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())
