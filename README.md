# gitlab-issue-analyzer

Täglicher Batch-Analyzer der GitLab-Issues auf Duplikate prüft, eine KI-Prioritätsliste erstellt und den Solver-Bot triggert.

## Was er macht

- **Duplikat-Erkennung** via multilingualer Sentence-Embeddings + LLM-Bestätigung
  - >90% Ähnlichkeit: direkter Kommentar im Issue + Label `bot::duplikat-prüfen`
  - 75–90% Ähnlichkeit: Hinweis in der Prioritätsliste
- **Bereits behoben**: neue Issues werden gegen geschlossene Issues (letzte 90 Tage) verglichen
- **KI-Prioritätsliste**: rankt alle offenen Issues per LLM (optional mit Unternehmenskontext) und erstellt/aktualisiert ein GitLab-Issue mit Label `bot::prioritätsliste`
- **Embedding-Cache**: bereits berechnete Embeddings werden gecacht, nur neue/geänderte Issues werden neu eingebettet
- **LLM-Kosten**: Ranking-Calls laufen nur wenn neue Issues vorhanden sind

## Pipeline-Kontext

```
Neues Issue
    → gitlab-issue-bot   (type::* + ki-ersteinschätzung::*)
    → gitlab-issue-analyzer  (+ bot::prio-gesetzt)  ← dieser Bot
    → gitlab-issue-solver    (+ bot::lösungsvorschlag)
```

## Endpoints

| Endpoint | Beschreibung |
|----------|-------------|
| `POST /analyze` | Analyse manuell starten |
| `GET /health` | Health-Check |

Die Analyse läuft automatisch täglich um 08:00 Uhr.

## Setup

### 1. Repo klonen und .env anlegen

```bash
git clone https://github.com/DESM0NDw/gitlab-issue-analyzer
cd gitlab-issue-analyzer
cp .env.example .env
```

`.env` ausfüllen:

```env
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_gitlab_token
GITLAB_PROJECT_ID=your_project_id

LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key

# Optional: gibt dem LLM Kontext für besseres Ranking
BUSINESS_CONTEXT=Wir sind ein B2B-SaaS für X. Kritisch sind: Y, Z.
```

### 2. Deployen

```bash
docker compose up -d --build
```

### 3. Analyse manuell starten

```bash
curl -X POST "https://your-domain/analyze"
```

## Konfiguration

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `GITLAB_URL` | `https://gitlab.com` | GitLab-Instanz URL |
| `GITLAB_TOKEN` | — | Personal Access Token (Scope: api) |
| `GITLAB_PROJECT_ID` | — | Projekt-ID |
| `LLM_PROVIDER` | `groq` | `groq` / `openai` / `mistral` |
| `GROQ_API_KEY` | — | API-Key für Groq |
| `MAX_ISSUES` | `100` | Maximale Anzahl Issues pro Lauf |
| `CLOSED_ISSUES_DAYS` | `90` | Tage zurück für geschlossene Issues |
| `API_RATE_LIMIT` | `0.5` | Sekunden zwischen GitLab API-Calls |
| `DUPLICATE_HIGH_THRESHOLD` | `0.90` | Schwellenwert für direkten Duplikat-Kommentar |
| `DUPLICATE_MEDIUM_THRESHOLD` | `0.75` | Schwellenwert für Duplikat-Hinweis in Liste |
| `BUSINESS_CONTEXT` | leer | Unternehmenskontext für LLM-Priorisierung |
