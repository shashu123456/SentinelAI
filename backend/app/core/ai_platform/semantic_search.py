"""Semantic Search — TF-IDF based similarity search for vulnerabilities.

Enables natural language queries like "authentication problems" or
"data leakage through APIs" to find relevant findings.
"""

import math
import re
from collections import Counter


class SemanticSearchEngine:
    """Lightweight TF-IDF search engine for vulnerability findings."""

    def __init__(self):
        self._documents: dict[int, dict] = {}  # id -> {text, metadata}
        self._idf: dict[str, float] = {}
        self._tfidf_cache: dict[int, dict[str, float]] = {}
        self._dirty = True

    def add_finding(self, finding_id: int, finding: dict):
        """Index a finding for search."""
        text = self._extract_text(finding)
        self._documents[finding_id] = {
            "text": text,
            "metadata": finding,
            "tokens": self._tokenize(text),
        }
        self._dirty = True

    def add_findings(self, findings: list[dict]):
        """Index multiple findings."""
        for f in findings:
            fid = f.get("id", id(f))
            self.add_finding(fid, f)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search findings by natural language query."""
        if not self._documents:
            return []

        if self._dirty:
            self._rebuild_index()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_tfidf = self._compute_query_tfidf(query_tokens)

        scores = []
        for doc_id, doc_tfidf in self._tfidf_cache.items():
            score = self._cosine_similarity(query_tfidf, doc_tfidf)
            if score > 0.01:
                scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in scores[:limit]:
            doc = self._documents[doc_id]
            results.append(
                {
                    "id": doc_id,
                    "score": round(score, 4),
                    "metadata": doc["metadata"],
                }
            )

        return results

    def _extract_text(self, finding: dict) -> str:
        """Extract searchable text from a finding."""
        parts = [
            finding.get("vulnerability_name", ""),
            finding.get("description", ""),
            finding.get("owasp_category", ""),
            finding.get("cwe_id", ""),
            finding.get("affected_endpoint", ""),
            finding.get("impact", ""),
            finding.get("remediation", ""),
            finding.get("severity", ""),
        ]
        return " ".join(str(p) for p in parts if p)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into meaningful terms."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s\-_]", " ", text)
        tokens = text.split()
        # Remove very short tokens and stopwords
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "shall",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "and",
            "or",
            "but",
            "not",
            "no",
            "if",
            "when",
            "where",
            "how",
            "what",
            "which",
            "who",
            "whom",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "i",
            "me",
            "my",
            "we",
            "our",
            "you",
            "your",
        }
        return [t for t in tokens if len(t) > 2 and t not in stopwords]

    def _rebuild_index(self):
        """Rebuild TF-IDF index."""
        N = len(self._documents)
        if N == 0:
            return

        # Document frequency
        df: Counter[str] = Counter()
        token_counts: dict[int, Counter] = {}

        for doc_id, doc in self._documents.items():
            counts = Counter(doc["tokens"])
            token_counts[doc_id] = counts
            for token in counts:
                df[token] += 1

        # IDF
        self._idf = {}
        for token, freq in df.items():
            self._idf[token] = math.log(N / (1 + freq))

        # TF-IDF for each document
        self._tfidf_cache = {}
        for doc_id, counts in token_counts.items():
            total = sum(counts.values())
            if total == 0:
                continue
            tfidf = {}
            for token, count in counts.items():
                tf = count / total
                idf = self._idf.get(token, 0)
                tfidf[token] = tf * idf
            self._tfidf_cache[doc_id] = tfidf

        self._dirty = False

    def _compute_query_tfidf(self, tokens: list[str]) -> dict[str, float]:
        """Compute TF-IDF vector for a query."""
        counts = Counter(tokens)
        total = len(tokens)
        if total == 0:
            return {}

        tfidf = {}
        for token, count in counts.items():
            tf = count / total
            idf = self._idf.get(token, math.log(max(1, len(self._documents)) / 1))
            tfidf[token] = tf * idf
        return tfidf

    def _cosine_similarity(self, a: dict[str, float], b: dict[str, float]) -> float:
        """Compute cosine similarity between two TF-IDF vectors."""
        if not a or not b:
            return 0.0

        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0

        dot = sum(a[k] * b[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)


_engine = None


def get_semantic_search() -> SemanticSearchEngine:
    global _engine
    if _engine is None:
        _engine = SemanticSearchEngine()
    return _engine
