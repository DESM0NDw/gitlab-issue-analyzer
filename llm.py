import json
import httpx
from config import settings, LLM_CONFIG

_PRIORITY_PROMPT_BASE = """Du bist ein Issue-Triage-Assistent. Analysiere diese GitLab-Issues und erstelle eine priorisierte Liste.
{context_block}
Antworte ausschließlich mit JSON:
{{
  "issues": [
    {{
      "iid": <issue_iid>,
      "priority_rank": <1 = höchste Priorität>,
      "reason": "Kurze Begründung auf Deutsch"
    }}
  ]
}}"""

DUPLICATE_PROMPT = """Du bist ein Issue-Triage-Assistent. Entscheide ob diese zwei GitLab-Issues Duplikate sind.
Antworte ausschließlich mit JSON:
{
  "is_duplicate": true | false,
  "reason": "Kurze Begründung auf Deutsch"
}"""


async def _call_llm(messages: list[dict]) -> str:
    cfg = LLM_CONFIG.get(settings.llm_provider)
    api_key = getattr(settings, cfg["api_key_field"])

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": cfg["model"],
                "messages": messages,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


def _build_priority_prompt() -> str:
    context_block = (
        f"Unternehmenskontext:\n{settings.business_context}\n"
        if settings.business_context
        else ""
    )
    return _PRIORITY_PROMPT_BASE.format(context_block=context_block)


async def prioritize_batch(issues: list[dict]) -> list[dict]:
    items = "\n".join([f"- IID {i['iid']}: {i['title']}" for i in issues])
    content = await _call_llm([
        {"role": "system", "content": _build_priority_prompt()},
        {"role": "user", "content": items},
    ])
    return json.loads(content).get("issues", [])


async def check_duplicate(issue: dict, other: dict) -> dict:
    text = (
        f"Issue A (#{issue['iid']}): {issue['title']}\n{issue.get('description') or ''}\n\n"
        f"Issue B (#{other['iid']}): {other['title']}\n{other.get('description') or ''}"
    )
    content = await _call_llm([
        {"role": "system", "content": DUPLICATE_PROMPT},
        {"role": "user", "content": text},
    ])
    return json.loads(content)
