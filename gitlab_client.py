import asyncio
import httpx
from datetime import datetime, timedelta
from config import settings

HEADERS = {"PRIVATE-TOKEN": settings.gitlab_token}


def _url(path: str) -> str:
    return f"{settings.gitlab_url}/api/v4/projects/{settings.gitlab_project_id}{path}"


async def _get(client: httpx.AsyncClient, path: str, params: dict = {}) -> dict | list:
    await asyncio.sleep(settings.api_rate_limit)
    response = await client.get(_url(path), headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


async def fetch_open_issues() -> list[dict]:
    issues = []
    page = 1
    async with httpx.AsyncClient() as client:
        while len(issues) < settings.max_issues:
            batch = await _get(client, "/issues", {
                "state": "opened",
                "per_page": 100,
                "page": page,
                "not[labels]": "bot::analysiert",
            })
            if not batch:
                break
            issues.extend(batch)
            page += 1
    return issues[:settings.max_issues]


async def fetch_closed_issues() -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=settings.closed_issues_days)).isoformat()
    issues = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            batch = await _get(client, "/issues", {
                "state": "closed",
                "updated_after": since,
                "per_page": 100,
                "page": page,
            })
            if not batch:
                break
            issues.extend(batch)
            page += 1
    return issues


async def set_labels(issue_iid: int, labels: list[str]) -> None:
    async with httpx.AsyncClient() as client:
        await asyncio.sleep(settings.api_rate_limit)
        await client.put(
            _url(f"/issues/{issue_iid}"),
            headers=HEADERS,
            json={"add_labels": ",".join(labels)},
            timeout=10,
        )


async def post_comment(issue_iid: int, body: str) -> None:
    async with httpx.AsyncClient() as client:
        await asyncio.sleep(settings.api_rate_limit)
        await client.post(
            _url(f"/issues/{issue_iid}/notes"),
            headers=HEADERS,
            json={"body": body},
            timeout=10,
        )


async def create_or_update_priority_issue(body: str) -> None:
    async with httpx.AsyncClient() as client:
        existing = await _get(client, "/issues", {
            "labels": "bot::prioritätsliste",
            "state": "opened",
        })
        if existing:
            issue_iid = existing[0]["iid"]
            await asyncio.sleep(settings.api_rate_limit)
            await client.put(
                _url(f"/issues/{issue_iid}"),
                headers=HEADERS,
                json={"description": body},
                timeout=10,
            )
        else:
            await asyncio.sleep(settings.api_rate_limit)
            await client.post(
                _url("/issues"),
                headers=HEADERS,
                json={
                    "title": "KI-Prioritätsliste",
                    "description": body,
                    "labels": "bot::prioritätsliste",
                },
                timeout=10,
            )
