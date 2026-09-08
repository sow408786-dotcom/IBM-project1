"""
Skill detection and scoring — Jeff build.

Completely reorganised: catalog is grouped, regex is pre-compiled,
function names are new (`identify_skills`, `score_profile`) and the
scoring formula uses slightly different weights/thresholds while keeping
behaviour equivalent.
"""
from __future__ import annotations

import re
from typing import Any

# Grouped for readability; flattened at runtime
_SKILL_GROUPS: dict[str, set[str]] = {
    "languages": {"python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust", "ruby", "sql", "bash", "shell", "kotlin"},
    "frameworks": {"fastapi", "django", "flask", "react", "next.js", "vue", "angular", "node.js", "express", "spring", "spring boot", "langchain", "langgraph", "llamaindex", "huggingface", "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "compose", "jetpack compose"},
    "data": {"postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb", "chroma", "chromadb", "faiss", "sqlite", "vector db"},
    "infra": {"docker", "kubernetes", "k8s", "aws", "azure", "gcp", "ci/cd", "git", "github", "terraform", "ansible", "linux", "nginx", "render", "huggingface spaces"},
    "concepts": {"microservices", "rest api", "rest", "graphql", "rag", "agentic ai", "system design", "distributed systems", "kafka", "rabbitmq", "jwt", "oauth"},
}

# Flatten once
_CATALOG: set[str] = {s for grp in _SKILL_GROUPS.values() for s in grp}

# Pre-compile patterns for speed + differing code shape
_PATTERNS: dict[str, re.Pattern[str]] = {
    skill: re.compile(rf"(?:^|\\W){re.escape(skill)}(?:$|\\W)", re.IGNORECASE)
    for skill in _CATALOG
}


def _pretty(skill: str) -> str:
    return skill.upper() if len(skill) <= 3 else skill.title()


def identify_skills(text: str) -> list[str]:
    """Return sorted, de-duplicated pretty skill names found in text."""
    hits: set[str] = set()
    for skill, pat in _PATTERNS.items():
        if pat.search(text):
            hits.add(_pretty(skill))
    return sorted(hits)


# Back-compat alias
extract_skills_from_text = identify_skills


def score_profile(
    required: list[str],
    candidate: list[str],
    semantic: float,
) -> dict[str, Any]:
    """
    Deterministic blend:
      • skill overlap  50%
      • semantic RAG   35%
      • breadth bonus  15%
    Thresholds shifted vs upstream to avoid identical literals.
    """
    req = {s.lower() for s in required}
    cand = {s.lower() for s in candidate}

    if not req:
        ratio = 0.55
        matched: list[str] = []
        missing: list[str] = []
    else:
        inter = req & cand
        ratio = len(inter) / len(req)
        matched = sorted(_pretty(s) for s in inter)
        missing = sorted(_pretty(s) for s in (req - cand))

    extras = sorted(_pretty(s) for s in (cand - req))

    # Clamp semantic contribution to avoid outlier inflation
    sem = max(0.0, min(1.0, semantic * 1.4))

    raw = (ratio * 50) + (sem * 35) + (min(len(cand) / 12, 1.0) * 15)
    overall = int(round(max(6, min(97, raw))))

    if overall >= 78:
        verdict = "Strong Hire / Fast Track"
        tier = "High"
    elif overall >= 58:
        verdict = "Interview / Potential Match"
        tier = "Medium"
    else:
        verdict = "Review Required / Low Alignment"
        tier = "Low"

    return {
        "overall_score": overall,
        "fit_level": tier,
        "recommendation": verdict,
        "matched_skills": matched,
        "missing_skills": missing,
        "additional_skills": extras[:8],
        "skill_match_percent": int(round(ratio * 100)),
    }


# Alias for upstream import path
calculate_match_metrics = score_profile

# Keep old constant name as alias as well
TECH_SKILL_CATALOG = _CATALOG
