<div align="center">

# 🔍OmniSight

### Multimodal UI Self-Healing & RPA Agent

*An autonomous QA pipeline that detects visual UI bugs, self-heals them, and ships verified fixes as reviewable Pull Requests — without a human ever writing a line of CSS.*

[![Status](https://img.shields.io/badge/status-Week%204-blue)]()
[![Python](https://img.shields.io/badge/python-3.11+-yellow)]()
[![React](https://img.shields.io/badge/react-18-61DAFB)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688)]()
[![License](https://img.shields.io/badge/license-Internship%20Project-lightgrey)]()

**Infotact Solutions — Advanced Generative AI Engineering Internship**

</div>

---

## 📖 What is OmniSight?

Traditional UI test automation (Selenium, Cypress) breaks the moment a
developer renames a CSS class — and it has no concept of *visual*
correctness at all. A button can be clipped, overlapping, or invisible, and
a selector-based test will still report green.

**OmniSight replaces the assertion with a Vision-Language Model.**

A headless browser captures the real rendered page. A VLM looks at the
screenshot the way a human QA engineer would, describes what's actually
wrong, proposes a CSS fix, applies it, re-screenshots the result, and
verifies its own fix worked — before a single line of that fix is trusted
enough to reach GitHub.

1. 🌐 **Staging site** — the live app under test
2. 📸 **Playwright** captures a screenshot + DOM snapshot
3. 🧠 **VLM (Qwen2.5-VL 7B)** — "what's visually wrong here?"
4. 🩹 **Self-healing loop** — apply fix → re-screenshot → VLM re-verifies
5. 🔒 **DOM cross-check** — reject hallucinated or self-contradictory reports
6. 🚀 **GitHub PR** — confidence-gated, screenshots attached, auto-branched
7. 🖥️ **React QA Dashboard** — human approves or rejects, one click

---

## 🧩 Architecture

| Layer | Responsibility | Branch |
|---|---|---|
| 🧠 **AI / Automation** | VLM bug detection, self-healing loop, DOM cross-check, false-positive validation | `ML` |
| 🌐 **Frontend / Capture** | Playwright capture script, asset pipeline (HTML + CSS + JS + images per page) | `frontend` |
| ⚙️ **Pipeline / Backend** | FastAPI, GitHub integration (PyGithub), confidence gating, React QA dashboard | `backend-fastapi` |

Each track owns an independent piece of the loop; the backend is the layer
that stitches them together into one pipeline.

---

## 👥 Team & Week 4 Progress

### 🧠 ML — Vision & Self-Healing

- ✅ Migrated from LLaVA 1.5 7B → **Qwen2.5-VL 7B** after LLaVA's fixed-resolution CLIP projector was found to compress viewport-overflow bugs into invisibility
- ✅ Self-healing loop proven **consistent across 3 independent runs** on the real injected bug
- ✅ **Zero false positives** across 3 clean control pages (product page, multi-item cart, order confirmation) — proves the detector doesn't cry wolf
- ✅ **Contradiction guard** added: catches cases where the VLM's `bug_still_present: false` conflicts with its own explanation text, and fails safe instead of reporting a false "FIXED"
- 🔄 **In progress:** image chunking/cropping to focus the VLM strictly on the anomalous region — cuts tokens and latency, and reduces selector hallucination on complex pages

### 🌐 Frontend — Capture Pipeline

- ✅ Root-caused and fixed a 4-day asset-loading blocker: the original capture script saved HTML only, so React never hydrated and every re-evaluation screenshot came back blank
- ✅ Rebuilt the capture pipeline to save HTML + CSS + JS + images together per page (`screenshots/<page>/assets/`)
- ✅ Delivered a genuine, Playwright-captured "after" screenshot for the verified fix
- ✅ Provided assets for **8 pages** (more than the 3 requested), unblocking both the ML and backend tracks

### ⚙️ Backend — Pipeline & Integration

- ✅ **GitHub Integration** — PyGithub-driven branch creation, HTML commit, and PR opening, gated so only self-healing-verified fixes ever reach GitHub
- ✅ **Confidence-threshold review flag** — fixes below `0.6` confidence still open a PR, but are clearly marked `[NEEDS REVIEW]` instead of being silently merged or silently dropped
- ✅ **PR #6** — the correct, fully verified fix on the real injected bug, with before/after screenshots attached as proof
- ✅ **React QA Dashboard** — FastAPI endpoints (`/prs`, approve, reject) + a color-coded React UI so a QA manager can approve or reject automated PRs in one click, no GitHub access required
- ✅ Repo hygiene — superseded PRs closed with explanatory comments, stray test branches pruned

---

## 🛠️ Tech Stack

<table>
<tr>
<td valign="top" width="33%">

**AI / Vision**
- Qwen2.5-VL 7B (Ollama)
- Playwright (Python)
- BeautifulSoup

</td>
<td valign="top" width="33%">

**Backend**
- FastAPI
- PyGithub
- Pydantic

</td>
<td valign="top" width="33%">

**Frontend**
- React 18 + Vite
- Fetch API

</td>
</tr>
</table>

---

## 🚀 Quick Start

```bash
# 1. Backend
cd backend/app
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 2. Dashboard
cd dashboard
npm install
npm run dev

# 3. Self-healing loop (ML)
cd ML
python vlm_test.py
```

Dashboard: `http://localhost:5173` · API docs: `http://localhost:8000/docs`

---

## 📅 Week-wise Roadmap

| Week | AI / Automation | Pipeline / Integration | Status |
|---|---|---|---|
| 1 | Browser automation, responsive screenshots | FastAPI webhook scaffolding | ✅ |
| 2 | Multimodal prompting, VLM bug detection | Action Engine — parse & validate VLM output | ✅ |
| 3 | Self-healing loop (apply fix → re-verify) | GitHub Integration (PyGithub) | ✅ |
| 4 | Image chunking/cropping optimization | React QA review dashboard | 🔄 |

---

## 🔐 Safety Design

OmniSight never trusts a single model's output at face value:

1. **DOM cross-check** — every claimed UI element must actually exist in the real page HTML
2. **Self-consistency check** — a report can't say "no bug" while describing one
3. **Confidence gating** — low-confidence fixes reach a human, never a silent merge
4. **Human-in-the-loop dashboard** — nothing merges without an explicit approve click

---

<div align="center">

*Built as part of Infotact Solutions' Advanced Generative AI Engineering internship program.*

</div>