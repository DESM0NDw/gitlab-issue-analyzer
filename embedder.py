from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def embed_issues(issues: list[dict]) -> np.ndarray:
    model = _get_model()
    texts = [f"{i['title']} {i.get('description') or ''}" for i in issues]
    return model.encode(texts, show_progress_bar=False)


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
