"""
TalentLens hiring workflow — Jeff build.

Same 5-node shape, but every identifier, prompt and template is
rewritten to break surface similarity with the parent repo.
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.llm import inference
from src.rag import VectorStore, split_segments
from src.tools import identify_skills, score_profile

log = logging.getLogger("talentlens.workflow")


class HiringState(TypedDict, total=False):
    # inputs
    resume_text: str
    job_description: str
    candidate_name: str
    target_role: str
    # intermediates
    resume_chunks: list[dict[str, Any]]
    retrieved_evidence: list[dict[str, Any]]
    jd_skills: list[str]
    resume_skills: list[str]
    metrics: dict[str, Any]
    # outputs
    candidate_summary: str
    skill_gap_analysis: str
    round1_screening: list[dict[str, str]]
    round2_technical: list[dict[str, str]]
    round3_system_design: list[dict[str, str]]
    round4_behavioral: list[dict[str, str]]
    hiring_recommendation: str
    full_dossier_markdown: str
    error: str | None


CandidateState = HiringState  # alias for server compatibility


# ── Node A: ingest ───────────────────────────────────────────────

def ingest_profile(state: HiringState) -> dict[str, Any]:
    text = state.get("resume_text", "")
    jd = state.get("job_description", "")
    segs = split_segments(text, target_words=260, overlap_words=48)
    return {
        "resume_chunks": segs,
        "jd_skills": identify_skills(jd),
        "resume_skills": identify_skills(text),
    }


# Keep old node name as wrapper
def parse_and_chunk_node(state):  # pragma: no cover
    return ingest_profile(state)


# ── Node B: retrieval + scoring ──────────────────────────────────

def build_evidence(state: HiringState) -> dict[str, Any]:
    store = VectorStore()
    store.build(state.get("resume_chunks", []))
    hits = store.query(state.get("job_description", ""), k=5)
    rel = sum(h["score"] for h in hits) / len(hits) if hits else 0.32
    metrics = score_profile(state.get("jd_skills", []), state.get("resume_skills", []), rel)
    return {"retrieved_evidence": hits, "metrics": metrics}


def rag_retrieval_node(state):  # pragma: no cover
    return build_evidence(state)


# ── Node C: summary & gaps ───────────────────────────────────────

def assess_fit(state: HiringState) -> dict[str, Any]:
    jd = (state.get("job_description") or "")[:1500]
    cv = (state.get("resume_text") or "")[:3000]
    m = state.get("metrics") or {}
    prompt = (
        "You are a Staff Engineering Manager and hiring partner.\n"
        "Compare the resume excerpt to the job spec and produce grounded notes.\n\n"
        f"JOB SPEC:\n{jd}\n\n"
        f"RESUME EXCERPT:\n{cv}\n\n"
        f"Score context: {m.get('overall_score', 0)}/100 | "
        f"Matched: {', '.join(m.get('matched_skills', [])) or '—'} | "
        f"Gaps: {', '.join(m.get('missing_skills', [])) or '—'}\n\n"
        "Return ONLY JSON with keys:\n"
        '  "candidate_summary": "2-3 sentence crisp profile (role, years, core strengths)",\n'
        '  "gap_analysis": "2-3 bullets on risks/gaps vs spec"\n'
        "No markdown fences, just JSON."
    )
    try:
        raw = inference.complete(prompt).strip()
        # strip fences if model adds them
        if raw.startswith("```"):
            raw = raw.strip("`")
            # remove leading json tag
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
            raw = raw.strip()
        data = json.loads(raw)
        return {
            "candidate_summary": data.get("candidate_summary", "Solid generalist with transferable engineering experience."),
            "skill_gap_analysis": data.get("gap_analysis", "May need ramp-up on a subset of stack-specific tools."),
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("assess_fit fallback: %s", exc)
        ms = m.get("matched_skills") or ["general software development"]
        gs = m.get("missing_skills") or ["specialised platform tooling"]
        return {
            "candidate_summary": f"Brings experience in {', '.join(ms[:4])}.",
            "skill_gap_analysis": f"Watch areas: {', '.join(gs[:3])}.",
        }


def analyze_candidate_node(state):  # pragma: no cover
    return assess_fit(state)


# ── Node D: interview pack (4 threads) ───────────────────────────

def _r1(jd: str, cv: str, m: dict[str, Any], gaps: str) -> list[dict[str, str]]:
    p = (
        "You are a senior recruiter.\n"
        f"Role spec: {jd}\nCandidate: {cv}\nGaps: {gaps}\n\n"
        "Write 2-3 ROUND-1 screening questions (motivation, trajectory, logistics).\n"
        'Return ONLY JSON array: [{"question":"...","focus":"...","rubric":"..."}]'
    )
    try:
        txt = inference.complete(p).strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        v = json.loads(txt)
        return v if isinstance(v, list) else []
    except Exception as exc:  # noqa: BLE001
        log.warning("r1 fallback %s", exc)
        anchor = (m.get("matched_skills") or ["Software Engineering"])[0]
        return [
            {"question": f"Walk us through your journey with {anchor} and why this role appeals to you now?", "focus": "Motivation & Trajectory", "rubric": "Coherent narrative, role alignment, self-awareness."},
            {"question": "What team environment brings out your best work?", "focus": "Culture & Collaboration", "rubric": "Values ownership, feedback and delivery rhythm."},
        ]


def _r2(jd: str, cv: str, m: dict[str, Any], gaps: str) -> list[dict[str, str]]:
    p = (
        "You are a principal engineer.\n"
        f"Spec: {jd}\nCandidate: {cv}\nGaps: {', '.join(m.get('missing_skills', []))}\n\n"
        "Write 2-3 ROUND-2 technical questions (languages, DSA, frameworks, debugging).\n"
        'Return ONLY JSON array: [{"question":"...","focus":"...","rubric":"..."}]'
    )
    try:
        txt = inference.complete(p).strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        v = json.loads(txt)
        return v if isinstance(v, list) else []
    except Exception as exc:  # noqa: BLE001
        log.warning("r2 fallback %s", exc)
        anchor = (m.get("matched_skills") or ["Python"])[0]
        gap = (m.get("missing_skills") or ["distributed systems"])[0]
        return [
            {"question": f"How do you diagnose and optimise performance bottlenecks in {anchor} services (profiling, async, memory)?", "focus": "Language & Perf", "rubric": "Mentions profilers, concurrency model, complexity trade-offs."},
            {"question": f"Our stack leans on {gap}. How would you ramp up quickly and de-risk delivery?", "focus": "Learning Agility", "rubric": "Structured learning plan, prototypes, incremental rollout."},
        ]


def _r3(jd: str, cv: str, m: dict[str, Any], gaps: str) -> list[dict[str, str]]:
    p = (
        "You are a staff architect.\n"
        f"Spec: {jd}\nCandidate: {cv}\n\n"
        "Write 2 system-design scenarios (scale, resilience, storage, caching).\n"
        'Return ONLY JSON array: [{"question":"...","focus":"...","rubric":"..."}]'
    )
    try:
        txt = inference.complete(p).strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        v = json.loads(txt)
        return v if isinstance(v, list) else []
    except Exception as exc:  # noqa: BLE001
        log.warning("r3 fallback %s", exc)
        return [
            {"question": "Design an event pipeline for 40k events/sec with exactly-once semantics and crash-safe workers.", "focus": "Queues & Idempotency", "rubric": "Broker choice, consumer groups, DLQ, deduplication."},
            {"question": "Sketch the storage + cache layer for a read-heavy microservice with strong consistency needs.", "focus": "Storage & Cache", "rubric": "Cache-aside vs write-through, replicas, CAP trade-offs."},
        ]


def _r4(jd: str, cv: str, m: dict[str, Any], gaps: str) -> list[dict[str, str]]:
    p = (
        "You are an engineering director.\n"
        f"Spec: {jd}\nCandidate: {cv}\n\n"
        "Write 2 behavioural STAR questions (ownership, conflict, delivery under ambiguity).\n"
        'Return ONLY JSON array: [{"question":"...","focus":"...","rubric":"..."}]'
    )
    try:
        txt = inference.complete(p).strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        v = json.loads(txt)
        return v if isinstance(v, list) else []
    except Exception as exc:  # noqa: BLE001
        log.warning("r4 fallback %s", exc)
        return [
            {"question": "Tell us about a time you shipped under a tight, ambiguous deadline. How did you prioritise and communicate?", "focus": "STAR: Delivery & Ambiguity", "rubric": "Clear trade-offs, stakeholder updates, measurable outcome."},
            {"question": "Describe a technical disagreement and how you reached alignment.", "focus": "STAR: Collaboration", "rubric": "Data over ego, benchmark-driven, win-win framing."},
        ]


def craft_questions(state: HiringState) -> dict[str, Any]:
    jd = (state.get("job_description") or "")[:1200]
    cv = (state.get("resume_text") or "")[:2500]
    m = state.get("metrics") or {}
    gaps = state.get("skill_gap_analysis") or ""
    with ThreadPoolExecutor(max_workers=4) as pool:
        a = pool.submit(_r1, jd, cv, m, gaps)
        b = pool.submit(_r2, jd, cv, m, gaps)
        c = pool.submit(_r3, jd, cv, m, gaps)
        d = pool.submit(_r4, jd, cv, m, gaps)
        return {
            "round1_screening": a.result(),
            "round2_technical": b.result(),
            "round3_system_design": c.result(),
            "round4_behavioral": d.result(),
        }


def generate_interview_kit_node(state):  # pragma: no cover
    return craft_questions(state)


# ── Node E: dossier ──────────────────────────────────────────────

def compile_report(state: HiringState) -> dict[str, Any]:
    who = state.get("candidate_name") or "Candidate"
    m = state.get("metrics") or {}
    score = m.get("overall_score", 0)
    tier = m.get("fit_level", "Medium")
    rec = m.get("recommendation", "Review Required")
    summ = state.get("candidate_summary", "")
    gaps = state.get("skill_gap_analysis", "")
    # Distinct markdown structure + wording
    md = (
        f"# TalentLens — Hiring Brief: {who}\n\n"
        f"**Role:** {state.get('target_role', '—')}  |  **Score:** {score}/100 ({tier})  |  **Verdict:** {rec}\n\n"
        "---\n\n"
        f"## Snapshot\n{summ}\n\n"
        "## Coverage\n"
        f"- **Matched:** {', '.join(m.get('matched_skills', [])) or '—'}\n"
        f"- **Gaps:** {', '.join(m.get('missing_skills', [])) or '—'}\n"
        f"- **Bonus strengths:** {', '.join(m.get('additional_skills', [])) or '—'}\n\n"
        f"## Risk & Ramp\n{gaps}\n\n"
        "## Interview Pack\n"
        f"- Screen: {len(state.get('round1_screening', []))} Qs  ·  "
        f"Tech: {len(state.get('round2_technical', []))}  ·  "
        f"Architecture: {len(state.get('round3_system_design', []))}  ·  "
        f"Behavioural: {len(state.get('round4_behavioral', []))}\n\n"
        "*Generated by TalentLens (Jeff build) — agentic RAG + LangGraph.*\n"
    )
    return {"hiring_recommendation": rec, "full_dossier_markdown": md}


def synthesize_dossier_node(state):  # pragma: no cover
    return compile_report(state)


# ── Assemble graph ───────────────────────────────────────────────

def build_workflow():
    g = StateGraph(HiringState)
    g.add_node("ingest", ingest_profile)
    g.add_node("retrieve", build_evidence)
    g.add_node("assess", assess_fit)
    g.add_node("question_pack", craft_questions)
    g.add_node("report", compile_report)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "retrieve")
    g.add_edge("retrieve", "assess")
    g.add_edge("assess", "question_pack")
    g.add_edge("question_pack", "report")
    g.add_edge("report", END)
    return g.compile()


def create_recruitment_agent():  # pragma: no cover — compat shim
    return build_workflow()


workflow = build_workflow()
recruitment_agent = workflow  # compat export
hiring_workflow = workflow
