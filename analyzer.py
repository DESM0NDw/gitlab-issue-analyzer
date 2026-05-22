import logging
from datetime import datetime
from embedder import embed_issues, find_similar_pairs
from llm import prioritize_batch, check_duplicate
from gitlab_client import (
    fetch_open_issues,
    fetch_closed_issues,
    set_labels,
    post_comment,
    create_or_update_priority_issue,
)
from config import settings

log = logging.getLogger(__name__)


async def run_analysis() -> dict:
    log.info("Analyse gestartet")

    open_issues = await fetch_open_issues()
    closed_issues = await fetch_closed_issues()
    log.info(f"{len(open_issues)} offene, {len(closed_issues)} geschlossene Issues geladen")

    if not open_issues:
        return {"status": "ok", "message": "Keine neuen Issues zu analysieren"}

    open_embeddings = embed_issues(open_issues)
    closed_embeddings = embed_issues(closed_issues) if closed_issues else None

    # Duplikate unter offenen Issues finden
    open_pairs = find_similar_pairs(
        open_issues, open_embeddings,
        open_issues, open_embeddings,
        settings.duplicate_high_threshold,
        settings.duplicate_medium_threshold,
    )

    # Ähnliche geschlossene Issues finden
    closed_pairs = []
    if closed_issues and closed_embeddings is not None:
        closed_pairs = find_similar_pairs(
            open_issues, open_embeddings,
            closed_issues, closed_embeddings,
            settings.duplicate_high_threshold,
            settings.duplicate_medium_threshold,
        )

    # Duplikat-Verdacht prüfen und kommentieren
    high_duplicates = []
    medium_duplicates = []
    seen_pairs = set()

    for pair in open_pairs:
        key = tuple(sorted([pair["issue"]["iid"], pair["similar"]["iid"]]))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        result = await check_duplicate(pair["issue"], pair["similar"])
        if not result.get("is_duplicate"):
            continue

        if pair["level"] == "high":
            high_duplicates.append({**pair, "reason": result["reason"]})
            comment = (
                f"**Mögliches Duplikat gefunden** ({int(pair['score'] * 100)}% Ähnlichkeit)\n\n"
                f"Dieses Issue ähnelt stark #{pair['similar']['iid']}: "
                f"[{pair['similar']['title']}]({pair['similar']['web_url']})\n\n"
                f"**Einschätzung:** {result['reason']}\n\n"
                f"Bitte prüfen und antworten:\n"
                f"- `/duplikat-ja` → wird als Duplikat geschlossen\n"
                f"- `/duplikat-nein` → Markierung wird entfernt\n\n"
                f"---\n*Automatisch generiert von gitlab-issue-analyzer*"
            )
            await post_comment(pair["issue"]["iid"], comment)
            await set_labels(pair["issue"]["iid"], ["bot::duplikat-prüfen"])
        else:
            medium_duplicates.append({**pair, "reason": result["reason"]})

    # Bereits gefixt in geschlossenen Issues
    already_fixed = []
    for pair in closed_pairs:
        result = await check_duplicate(pair["issue"], pair["similar"])
        if result.get("is_duplicate"):
            already_fixed.append({**pair, "reason": result["reason"]})
            comment = (
                f"**Ähnliches Issue bereits geschlossen**\n\n"
                f"#{pair['similar']['iid']} [{pair['similar']['title']}]"
                f"({pair['similar']['web_url']}) wurde bereits geschlossen "
                f"und könnte dieses Problem abdecken.\n\n"
                f"**Einschätzung:** {result['reason']}\n\n"
                f"---\n*Automatisch generiert von gitlab-issue-analyzer*"
            )
            await post_comment(pair["issue"]["iid"], comment)

    # Prioritäten erstellen (Batches von 10)
    all_priorities = []
    batch_size = 10
    for i in range(0, len(open_issues), batch_size):
        batch = open_issues[i:i + batch_size]
        result = await prioritize_batch(batch)
        all_priorities.extend(result)

    all_priorities.sort(key=lambda x: x.get("priority_rank", 999))

    # Labels setzen
    for issue in open_issues:
        await set_labels(issue["iid"], ["bot::prio-gesetzt"])

    # Prioritätsliste als GitLab-Issue erstellen/aktualisieren
    await create_or_update_priority_issue(_build_report(
        open_issues, all_priorities, medium_duplicates, already_fixed
    ))

    log.info("Analyse abgeschlossen")
    return {
        "status": "ok",
        "analyzed": len(open_issues),
        "high_duplicates": len(high_duplicates),
        "medium_duplicates": len(medium_duplicates),
        "already_fixed": len(already_fixed),
    }


def _build_report(
    issues: list[dict],
    priorities: list[dict],
    medium_duplicates: list[dict],
    already_fixed: list[dict],
) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    issue_map = {i["iid"]: i for i in issues}

    lines = [
        f"# KI-Prioritätsliste",
        f"*Zuletzt aktualisiert: {now}*\n",
        "## Priorisierte Issues\n",
    ]

    for rank, p in enumerate(priorities, 1):
        issue = issue_map.get(p["iid"])
        if not issue:
            continue
        lines.append(
            f"{rank}. #{p['iid']} [{issue['title']}]({issue['web_url']})  \n"
            f"   *{p.get('reason', '')}*\n"
        )

    if medium_duplicates:
        lines.append("\n## Zur Prüfung: Mögliche Duplikate\n")
        for d in medium_duplicates:
            lines.append(
                f"- #{d['issue']['iid']} könnte Duplikat von "
                f"#{d['similar']['iid']} sein "
                f"({int(d['score'] * 100)}%) — {d['reason']}\n"
            )

    if already_fixed:
        lines.append("\n## Möglicherweise bereits behoben\n")
        for d in already_fixed:
            lines.append(
                f"- #{d['issue']['iid']} ähnelt dem geschlossenen "
                f"#{d['similar']['iid']} — {d['reason']}\n"
            )

    lines.append("\n---\n*Automatisch generiert von gitlab-issue-analyzer*")
    return "\n".join(lines)
