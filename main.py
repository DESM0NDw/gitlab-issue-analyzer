import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from analyzer import run_analysis

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_analysis, "cron", hour=8, minute=0)
    scheduler.start()
    log.info("Scheduler gestartet, täglicher Lauf um 08:00 Uhr")
    yield
    scheduler.shutdown()


app = FastAPI(title="GitLab Issue Analyzer", lifespan=lifespan)


@app.post("/analyze")
async def analyze():
    try:
        result = await run_analysis()
        return result
    except Exception as e:
        log.error(f"Analyse fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
