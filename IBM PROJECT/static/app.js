// TalentLens — Jeff build. Class-based controller, distinct from upstream.
class TalentLensApp {
  constructor() {
    this.activeRound = "round1";
    this.lastPayload = null;
    this.els = {};
  }

  // —— presets (renamed vs upstream) ——
  PRESET_SENIOR_JD = `Role: Senior Agentic AI & Systems Engineer
Experience: 4-6 yrs · Remote/Hybrid

Mission: Lead our agentic platform — LangGraph workflows, RAG retrieval,
and resilient Python microservices.

Must-haves:
- Python, SQL, Bash
- LangChain / LangGraph / RAG / Vector DBs (Chroma, FAISS)
- FastAPI, async, microservices
- PostgreSQL, Redis
- Docker, Kubernetes, Git, CI/CD`;

  PRESET_SENIOR_CV = `Alex Chen — Lead AI & Backend Engineer
San Francisco · alex.chen@example.com

Summary: 5+ yrs shipping Python + Agentic AI systems (LangGraph, RAG) at scale.

Skills: Python, SQL, Bash · LangChain, LangGraph, RAG, Chroma/FAISS
FastAPI/Flask, async · Postgres, Redis, SQLite · Docker/K8s, GitHub Actions

Experience:
- Nova Tech (2022–): Multi-agent routing workflow; RAG engine 120k q/day p95 <180ms; K8s 99.95% uptime.
- Apex Cloud (2019–22): Flask/Postgres APIs; CI/CD; 92% PyTest coverage.

Education: B.S. CS, UC Davis (2019)`;

  PRESET_JUNIOR_JD = `Role: Junior Python Backend Developer
- 1–2 yrs Python & REST
- Postgres/MySQL, Docker, Git, tests
- Eagerness to learn AI/microservices`;

  PRESET_JUNIOR_CV = `Priya Sharma — Junior Python Dev
priya.s@example.com · B.Tech CS, Anna Univ (2024)
Skills: Python, JS, SQL · Django/Flask, Pandas · Git, SQLite, Postman
Projects: Flask + SQLite inventory API (JWT); BeautifulSoup campus scraper.`;

  init() {
    this.cacheEls();
    this.bindTheme();
    this.bindPresets();
    this.bindUploader();
    this.bindTracker();
    this.bindTabs();
    this.bindForm();
    this.bindCopy();
    this.fillSenior();
  }

  cacheEls() {
    const $ = (id) => document.getElementById(id);
    this.els = {
      app: $("appContainer"),
      form: $("evaluationForm"),
      name: $("candidateName"),
      role: $("targetRole"),
      jd: $("jobDescription"),
      cv: $("resumeText"),
      file: $("resumePdf"),
      drop: $("dropArea"),
      dropText: $("dropText"),
      submit: $("btnSubmit"),
      tracker: $("pipelineCard"),
      badge: $("pipelineStatusBadge"),
      results: $("resultsContent"),
      score: $("scoreValue"),
      verdict: $("recBanner"),
      summary: $("candidateSummaryText"),
      ok: $("matchedSkillsRow"),
      gaps: $("missingSkillsRow"),
      questions: $("questionsContainer"),
      copy: $("btnCopyDossier"),
    };
  }

  // theme
  bindTheme() {
    const light = document.getElementById("themeLight");
    const dark = document.getElementById("themeDark");
    const apply = (t) => {
      document.documentElement.setAttribute("data-theme", t);
      localStorage.setItem("talentlens_theme", t);
      light.classList.toggle("is-active", t === "light");
      dark.classList.toggle("is-active", t === "dark");
    };
    const saved = localStorage.getItem("talentlens_theme") || "light";
    apply(saved);
    light.addEventListener("click", () => apply("light"));
    dark.addEventListener("click", () => apply("dark"));
  }

  bindPresets() {
    document.getElementById("btnPresetSenior").addEventListener("click", () => this.fillSenior());
    document.getElementById("btnPresetJunior").addEventListener("click", () => this.fillJunior());
    document.getElementById("btnReset").addEventListener("click", () => this.resetForm());
  }

  fillSenior() {
    this.els.name.value = "Alex Chen";
    this.els.role.value = "Senior Agentic AI & Systems Engineer";
    this.els.jd.value = this.PRESET_SENIOR_JD;
    this.els.cv.value = this.PRESET_SENIOR_CV;
    this.clearFileLabel();
  }
  fillJunior() {
    this.els.name.value = "Priya Sharma";
    this.els.role.value = "Junior Python Developer";
    this.els.jd.value = this.PRESET_JUNIOR_JD;
    this.els.cv.value = this.PRESET_JUNIOR_CV;
    this.clearFileLabel();
  }
  resetForm() {
    this.els.name.value = "";
    this.els.role.value = "";
    this.els.jd.value = "";
    this.els.cv.value = "";
    this.els.file.value = "";
    this.clearFileLabel();
    this.els.name.focus();
  }
  clearFileLabel() {
    this.els.dropText.innerHTML = "<strong>Choose PDF</strong> or drag & drop";
    this.els.file.value = "";
  }

  bindUploader() {
    const { drop, file, dropText } = this.els;
    drop.addEventListener("click", () => file.click());
    file.addEventListener("change", () => {
      if (file.files.length) dropText.innerHTML = `Loaded: <strong>${file.files[0].name}</strong> (${Math.round(file.files[0].size / 1024)} KB)`;
    });
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("is-dragover"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("is-dragover"); }));
    drop.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length) {
        file.files = e.dataTransfer.files;
        dropText.innerHTML = `Loaded: <strong>${e.dataTransfer.files[0].name}</strong>`;
      }
    });
  }

  bindTracker() {
    const head = document.getElementById("pipelineHeader");
    const card = document.getElementById("pipelineCard");
    if (head && card) head.addEventListener("click", () => card.classList.toggle("is-collapsed"));
  }

  bindTabs() {
    document.querySelectorAll(".tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        this.activeRound = btn.dataset.round;
        this.renderQuestions();
      });
    });
  }

  bindCopy() {
    this.els.copy.addEventListener("click", async () => {
      if (!this.lastPayload?.dossier_markdown) return;
      await navigator.clipboard.writeText(this.lastPayload.dossier_markdown);
      const prev = this.els.copy.textContent;
      this.els.copy.textContent = "Copied";
      setTimeout(() => (this.els.copy.textContent = prev), 1400);
    });
  }

  bindForm() {
    this.els.form.addEventListener("submit", (e) => this.onSubmit(e));
  }

  async onSubmit(e) {
    e.preventDefault();
    const fd = new FormData(this.els.form);
    this.els.submit.disabled = true;
    this.els.submit.textContent = "Running…";

    // open layout
    this.els.app.classList.remove("is-centered");
    this.els.app.classList.add("is-open");
    this.els.tracker.classList.remove("is-collapsed");
    this.resetSteps();
    this.setStep("step1", "is-active");
    this.els.badge.textContent = "Running";

    const t1 = setTimeout(() => { this.setStep("step1", "is-done"); this.setStep("step2", "is-active"); }, 750);
    const t2 = setTimeout(() => { this.setStep("step2", "is-done"); this.setStep("step3", "is-active"); }, 1650);
    const t3 = setTimeout(() => { this.setStep("step3", "is-done"); this.setStep("step4", "is-active"); }, 2850);

    try {
      const res = await fetch("/api/evaluate", { method: "POST", body: fd });
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Request failed");
      }
      const data = await res.json();
      this.lastPayload = data;
      for (let i = 1; i <= 5; i++) this.setStep(`step${i}`, "is-done");
      this.els.badge.textContent = "Done";
      this.renderResults(data);
      setTimeout(() => this.els.tracker.classList.add("is-collapsed"), 600);
    } catch (err) {
      alert(`Assessment error: ${err.message}`);
      this.resetSteps();
      this.els.badge.textContent = "Failed";
    } finally {
      this.els.submit.disabled = false;
      this.els.submit.innerHTML = '<span class="btn__icon">▶</span> Run Assessment';
    }
  }

  resetSteps() {
    for (let i = 1; i <= 5; i++) {
      const el = document.getElementById(`step${i}`);
      if (el) el.className = "tracker__step";
    }
  }
  setStep(id, state) {
    const el = document.getElementById(id);
    if (el) el.className = `tracker__step ${state}`;
  }

  renderResults(data) {
    this.els.results.style.display = "block";
    this.els.copy.style.display = "inline-flex";
    const m = data.metrics || {};
    this.els.score.textContent = `${m.overall_score ?? 0}%`;
    this.els.verdict.textContent = `Verdict: ${m.recommendation || "Review Required"}`;
    this.els.summary.textContent = data.candidate_summary || "";

    const ok = this.els.ok, gaps = this.els.gaps;
    ok.innerHTML = "";
    (m.matched_skills || []).forEach((s) => {
      const span = document.createElement("span");
      span.className = "chip chip--ok";
      span.textContent = s;
      ok.appendChild(span);
    });
    if (!m.matched_skills?.length) ok.innerHTML = '<span class="chip chip--muted">—</span>';

    gaps.innerHTML = "";
    (m.missing_skills || []).forEach((s) => {
      const span = document.createElement("span");
      span.className = "chip chip--warn";
      span.textContent = s;
      gaps.appendChild(span);
    });
    if (!m.missing_skills?.length) gaps.innerHTML = '<span class="chip chip--ok">Full coverage</span>';

    this.renderQuestions();
  }

  renderQuestions() {
    if (!this.lastPayload?.rounds) return;
    const map = { round1: "round1_screening", round2: "round2_technical", round3: "round3_system_design", round4: "round4_behavioral" };
    const key = map[this.activeRound];
    const list = this.lastPayload.rounds[key] || [];
    const box = this.els.questions;
    box.innerHTML = "";
    if (!list.length) {
      box.innerHTML = '<div style="color:var(--muted);font-size:.86rem;padding:12px">No questions for this round.</div>';
      return;
    }
    list.forEach((q, i) => {
      const el = document.createElement("div");
      el.className = "qcard";
      el.innerHTML = `
        <div class="qcard__head">
          <div class="qcard__q">Q${i + 1}: ${this.esc(q.question)}</div>
          <span class="qcard__tag">${this.esc(q.focus || "General")}</span>
        </div>
        <div class="qcard__rubric"><strong>Rubric:</strong> ${this.esc(q.rubric || "Assess depth & clarity.")}</div>
      `;
      box.appendChild(el);
    });
  }

  esc(s) {
    if (!s) return "";
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
}

document.addEventListener("DOMContentLoaded", () => new TalentLensApp().init());
