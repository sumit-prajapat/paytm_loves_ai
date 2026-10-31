import math
import re
from typing import Any

from app.rag.policies import SUPPORT_POLICIES


def tokenize(text: str) -> list[str]:
    """Tokenize Hindi, Hinglish, and English text into words."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [word for word in cleaned.split() if len(word) > 1]


class PolicyRetriever:
    """Local, offline, zero-dependency policy retriever with BM25-style scoring for support policies."""

    def __init__(self, policies: list[dict[str, Any]] | None = None) -> None:
        self.policies = policies or SUPPORT_POLICIES
        self.doc_tokens: list[list[str]] = []
        self.doc_len: list[int] = []
        self.df: dict[str, int] = {}
        self.total_docs = len(self.policies)

        for p in self.policies:
            tokens = tokenize(f"{p['title']} {p['text']}")
            self.doc_tokens.append(tokens)
            self.doc_len.append(len(tokens))
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.df[t] = self.df.get(t, 0) + 1

        self.avg_doc_len = sum(self.doc_len) / max(self.total_docs, 1)

    def search(self, query: str, top_k: int = 3, language: str | None = None) -> list[dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return self.policies[:top_k]

        scores: list[tuple[float, dict[str, Any]]] = []

        k1 = 1.5
        b = 0.75

        for idx, policy in enumerate(self.policies):
            # Optional language filter or preference
            lang_boost = 1.0
            if language and policy["language"] == language:
                lang_boost = 1.25

            doc = self.doc_tokens[idx]
            d_len = self.doc_len[idx]
            score = 0.0

            # Count term frequencies in this doc
            tf: dict[str, int] = {}
            for token in doc:
                tf[token] = tf.get(token, 0) + 1

            for q_term in query_tokens:
                if q_term in tf:
                    doc_freq = self.df.get(q_term, 1)
                    idf = math.log((self.total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                    term_tf = tf[q_term]
                    numerator = term_tf * (k1 + 1)
                    denominator = term_tf + k1 * (1 - b + b * (d_len / self.avg_doc_len))
                    score += idf * (numerator / denominator)

            score *= lang_boost
            scores.append((score, policy))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        max_score = scores[0][0] if scores and scores[0][0] > 0 else 1.0
        for s, p in scores[:top_k]:
            normalized_confidence = min(max(s / (max_score + 1e-5), 0.1), 1.0) if s > 0 else 0.5
            results.append({
                "id": p["id"],
                "title": p["title"],
                "text": p["text"],
                "language": p["language"],
                "score": round(s, 3),
                "confidence": round(normalized_confidence, 2),
            })
        return results


policy_retriever = PolicyRetriever()
