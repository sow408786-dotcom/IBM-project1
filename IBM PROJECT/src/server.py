"""
TalentLens FastAPI service — Jeff build.

Heavily restructured vs upstream: different app metadata, CORS,
renamed handlers, dual route (`/api/evaluate` + `/api/v1/assessment`),
and clearer separation of upload handling.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.config import APP_TITLE, APP_VERSION, HOST, PORT, UPLOADS_DIR
from src.graph import hiring_workflow
from src.rag import read_pdf_text

log = logging.getLogger("talentlens.api")

app = FastAPI(title=APP_TITLE, description="Agentic hiring copilot — LangGraph + RAG + Ollama", version=APP_VERSION)

# Allow local dev / preview origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets
ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
try:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def landing():
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        return HTMLResponse("<h1>TalentLens initialising…</h1>", status_code=200)
    return FileResponse(idx)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": APP_TITLE, "version": APP_VERSION}


def _extract_resume_text(resume_text: Optional[str], pdf: Optional[UploadFile]) -> str:
    if pdf and getattr(pdf, "filename", None):
        dest = UPLOADS_DIR / pdf.filename  # type: ignore[arg-type]
        try:
            with open(dest, "wb") as out:
                shutil.copyfileobj(pdf.file, out)
            return read_pdf_text(dest)
        except Exception as exc:  # noqa: BLE001
            log.error("pdf read failed: %s", exc)
            raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc
        finally:
            try:
                if dest.exists():
                    dest.unlink()
            except Exception:
                pass
    if resume_text and resume_text.strip():
        return resume_text.strip()
    return ""


def _run_workflow(candidate_name: str, target_role: str, jd: str, resume: str) -> dict:
    seed: dict = {
        "resume_text": resume,
        "job_description": jd,
        "candidate_name": candidate_name or "Candidate",
        "target_role": target_role or "Software Engineer",
        "resume_chunks": [],
        "retrieved_evidence": [],
        "jd_skills": [],
        "resume_skills": [],
        "metrics": {},
        "candidate_summary": "",
        "skill_gap_analysis": "",
        "round1_screening": [],
        "round2_technical": [],
        "round3_system_design": [],
        "round4_behavioral": [],
        "hiring_recommendation": "",
        "full_dossier_markdown": "",
        "error": None,
    }
    try:
        final = hiring_workflow.invoke(seed)
    except Exception as exc:  # noqa: BLE001
        log.exception("workflow failed")
        raise HTTPException(status_code=500, detail=f"Workflow error: {exc}") from exc

    return {
        "status": "success",
        "candidate_name": final.get("candidate_name"),
        "target_role": final.get("target_role"),
        "metrics": final.get("metrics"),
        "candidate_summary": final.get("candidate_summary"),
        "skill_gap_analysis": final.get("skill_gap_analysis"),
        "rounds": {
            "round1_screening": final.get("round1_screening", []),
            "round2_technical": final.get("round2_technical", []),
            "round3_system_design": final.get("round3_system_design", []),
            "round4_behavioral": final.get("round4_behavioral", []),
        },
        "hiring_recommendation": final.get("hiring_recommendation"),
        "dossier_markdown": final.get("full_dossier_markdown"),
    }


@app.post("/api/evaluate")
async def evaluate(
    candidate_name: Optional[str] = Form("Candidate"),
    target_role: Optional[str] = Form("Software Engineer"),
    job_description: str = Form(...),
    resume_text: Optional[str] = Form(None),
    resume_pdf: Optional[UploadFile] = File(None),
):
    resume = _extract_resume_text(resume_text, resume_pdf)
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a PDF or paste resume text.")
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
    return _run_workflow(candidate_name or "Candidate", target_role or "Software Engineer", job_description, resume)


# Alias route with Jeff naming — both work
@app.post("/api/v1/assessment")
async def assessment_alias(
    candidate_name: Optional[str] = Form("Candidate"),
    target_role: Optional[str] = Form("Software Engineer"),
    job_description: str = Form(...),
    resume_text: Optional[str] = Form(None),
    resume_pdf: Optional[UploadFile] = File(None),
):
    resume = _extract_resume_text(resume_text, resume_pdf)
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a PDF or paste resume text.")
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
    return _run_workflow(candidate_name or "Candidate", target_role or "Software Engineer", job_description, resume)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("src.server:app", host=HOST, port=PORT, reload=True)
