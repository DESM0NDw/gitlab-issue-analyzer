import pickle
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from config import settings

log = logging.getLogger(__name__)
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def _load_cache() -> dict:
    path = Path(settings.cache_path)
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    path = Path(settings.cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(cache, f)


def embed_issues(issues: list[dict]) -> np.ndarray:
    model = _get_model()
    cache = _load_cache()

    embeddings = []
    to_encode = []
    updated = False

    for issue in issues:
        key = f"{issue['iid']}_{issue.get('updated_at', '')}"
        if key in cache:
            embeddings.append(cache[key])
        else:
            to_encode.append((issue, key))
            embeddings.append(None)

    if to_encode:
        texts = [f"{i['title']} {i.get('description') or ''}" for i, _ in to_encode]
        new_embeddings = model.encode(texts, show_progress_bar=False)
        idx = 0
        for i, (issue, key) in enumerate(to_encode):
            pos = next(j for j, e in enumerate(embeddings) if e is None)
            cache[key] = new_embeddings[idx]
            embeddings[pos] = new_embeddings[idx]
            idx += 1
        updated = True
        log.info(f"Embeddings: {len(to_encode)} neu berechnet, {len(issues) - len(to_encode)} aus Cache")

    if updated:
        _save_cache(cache)

    return np.array(embeddings)


def find_similar_pairs(
    open_issues: list[dict],
    open_embeddings: np.ndarray,
    compare_issues: list[dict],
    compare_embeddings: np.ndarray,
    high_threshold: float,
    medium_threshold: float,
) -> list[dict]:
    similarities = cosine_similarity(open_embeddings, compare_embeddings)
    pairs = []

    for i, issue in enumerate(open_issues):
        for j, other in enumerate(compare_issues):
            if issue["iid"] == other.get("iid"):
                continue
            score = float(similarities[i][j])
            if score >= medium_threshold:
                pairs.append({
                    "issue": issue,
                    "similar": other,
                    "score": round(score, 3),
                    "level": "high" if score >= high_threshold else "medium",
                })

    pairs.sort(key=lambda x: x["score"], reverse=True)
    return pairs
