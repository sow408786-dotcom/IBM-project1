# TalentLens — AI HR Recruitment Assistant (TNSDC Use Case #2 · Jeff Build)

[![Track: IBM Agentic AI](https://img.shields.io/badge/TNSDC-IBM_Agentic_AI-4F46E5)](https://www.naanmudhalvan.tn.gov.in/)
[![Use Case #2](https://img.shields.io/badge/Use_Case-HR_Recruitment_Assistant-0F172A)](./data/samples/sample_senior_jd.txt)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-0F172A)](https://python.org)

> **Use Case #2 — AI HR Recruitment Assistant** — screens resumes, matches candidates with job descriptions and generates interview questions. Stack: **Agent + Tools + RAG** (Use Case #2, per TNSDC Project Plan §6). Jeff build is an independent implementation with distinct naming, prompts and UI.

---

## Program Alignment (TNSDC 5-Day Plan)

| Day | Focus (Plan) | Jeff Build Output |
|-----|--------------|-------------------|
| **D1** | Agentic AI & Project Foundation — use case selection, architecture, Python/LLM + Ollama | Use Case #2 selected, `src/config.py` + `src/llm.py` (`TalentLLM` / `gpt-oss:120b`), Ollama Cloud ready |
| **D2** | Building the AI Agent — model/tools/memory, tool-calling (LangChain), multi-tool agent | `src/tools.py` (`identify_skills`/`score_profile`), tool-calling tested |
| **D3** | LangGraph & Workflow — nodes/edges/state, memory & error handling | `src/graph.py` — `HiringState`, 5 nodes `ingest→retrieve→assess→question_pack→report`, `StateGraph` + `ThreadPoolExecutor` fan-out + fallbacks |
| **D4** | Agentic RAG + MCP — doc processing & retrieval, Agentic RAG, MCP intro | `src/rag.py` (`VectorStore{build,query}`), evidence-grounded Agentic RAG, MCP intro covered |
| **D5** | End-to-End & Demo — integrate, test, optimise, document, present | `src/server.py` (FastAPI + CORS), `static/` (Inter/Fraunces, indigo/slate), `POST /api/evaluate` → hiring brief, GitHub + LMS ready |

**Key capabilities (Plan §6):** Agent + Tools + RAG (MCP intro per §4/§5).

---

## What it does

- **RAG-grounded screen** — segments resume (`split_segments`), TF-IDF `VectorStore`, top-5 JD query, skill overlap + semantic blend `50/35/15` → `overall_score 0–100`, tier/verdict.
- **Gap analysis** — LLM JSON-forced summary + 2–3 risk bullets.
- **Interview pack (4 rounds, parallel)** — R1 screen · R2 technical · R3 architecture · R4 behavioural (STAR), each Q with rubric.
- **Hiring brief** — Markdown with coverage matrix, copyable via UI.

```
PDF/text → ingest (segment + skill ID) → retrieve (RAG → 5 hits) → assess (LLM) → question_pack (4 threads) → report
```

---

## Stack

Python 3.11 · FastAPI · Uvicorn · LangGraph · LangChain · scikit-learn · httpx · PyPDF · Ollama Cloud (`gpt-oss:120b`)

---

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # OLLAMA_API_KEY / OLLAMA_BASE_URL / OLLAMA_MODEL
python -m src.server   # http://localhost:8000 → TalentLens
# UI-only (no venv): python3 -m http.server 8001 --directory .  → http://localhost:8001/static/
```

Endpoints: `GET /` · `GET /api/health` · `POST /api/evaluate` (multipart `candidate_name`, `target_role`, `job_description`, `resume_text`, `resume_pdf`) + alias `POST /api/v1/assessment`

---

## Layout

```
Jeff/
├── src/  config, llm, rag, tools, graph, server
├── static/  index.html, styles.css, app.js
├── data/samples/  sample_senior_jd.txt + alex_chen resume (neutral)
└── uploads/ (temp, gitignored)
```

---

## Submission

- Final project + docs + GitHub link → Adroit ProLearn (LMS) Day 5 (§8)
- Quiz Day 3 on LMS, attendance QR x2/day, IBM CEP exam prep access

— Jeff build, TNSDC IBM Agentic AI Track, 31 Aug–4 Sep 2026.
