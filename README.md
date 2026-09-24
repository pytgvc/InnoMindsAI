# InnoMinds AI
**AI-Powered Innovation Management Platform — SIH 2026, Problem Statement IS-1**
Sponsored by Netlink Software Pvt. Ltd.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000**. Data files and charts are created automatically on first run.

**Demo accounts** (seeded automatically):
| Role | Username | Password |
|---|---|---|
| Employee | `employee` | `employee123` |
| Reviewer | `reviewer` | `reviewer123` |
| Admin | `admin` | `admin123` |

New employees can also self-register from the login page.

Run `python smoke_test.py` any time to exercise the full submit → review → approve → implement
lifecycle end-to-end against a throwaway dataset (it does not touch your real `data/` folder's
seeded accounts on a fresh run, but it does reset `data/` — don't run it against data you want to keep).

## Tech stack
Python, Flask, Jinja2, HTML/CSS/JavaScript, Pandas, NumPy, Matplotlib. No database — all
persistence is plain CSV files under `data/`, which keeps the whole thing inspectable and
easy to demo/reset for judges.

## How the requirements map to the code

| Requirement | Where |
|---|---|
| Idea submission (title, description, dept, category, cost, impact) | `submit_idea()` in `app.py`, `templates/submit_idea.html` |
| AI categorization / summary / problem / improvements / requirements / implementation plan | `ai_analysis.py` — keyword-weighted classifier, word-frequency extractive summarizer, cue-based problem detection, template-driven suggestions. Runs automatically on submission, fully offline (this **is** the local fallback — no external API key needed) |
| Duplicate/similar idea detection | `duplicate_detector.py` — hand-rolled TF‑IDF + cosine similarity (NumPy only) |
| Evaluation/prioritization (business value, feasibility, cost, strategic alignment, novelty, impact) | `evaluation.py: score_idea()` — weighted scoring formula, 0–100 final score, per-idea Matplotlib chart |
| Multi-level approval + role-based access + comments + notifications | `app.py` routes `evaluate()`/`decide()`, `auth.py` role decorators, `data_manager.py` comments/notifications tables |
| Lifecycle tracking | `status` field: `Submitted → Under Review → Pending Approval → Approved → Implemented` (or `Rejected` at either review stage) |
| Dashboards & analytics (totals, department contribution, implementation progress, ROI) | `evaluation.py` chart functions + `/analytics` route |
| AI recommendations (high-potential ideas, resource allocation, trends) | `evaluation.py: top_priority_ideas()`, `department_resource_recommendation()`, `trend_recommendation()` |

## Project structure

```
InnoMindsAI/
├── app.py                 # Flask routes, lifecycle/status logic
├── auth.py                # login + role-based access decorators
├── data_manager.py         # all CSV read/write (single source of truth)
├── ai_analysis.py          # local NLP-lite "AI" engine
├── duplicate_detector.py   # TF-IDF + cosine similarity
├── evaluation.py           # scoring formula + all Matplotlib charts
├── smoke_test.py           # end-to-end lifecycle test (Flask test client)
├── requirements.txt
├── data/                   # auto-created CSVs (users, ideas, comments, notifications)
├── static/
│   ├── css/style.css       # required sage-green palette, responsive layout
│   ├── js/main.js          # notification polling, table search, live sliders
│   └── charts/             # auto-generated PNG charts
└── templates/               # Jinja2 pages (dashboard, submit, idea detail, queues, analytics...)
```

## Notes
- Cost/impact/score fields are validated server-side (non-negative numbers, 0–10 score ranges,
  minimum description length) with user-facing error messages — nothing silently fails.
- Every button in the UI is wired to a real route; there are no placeholder/dead buttons.
- The evaluation weights (business value 25%, feasibility 20%, strategic alignment 20%,
  potential impact 15%, novelty 10%, cost 10%) live in one place (`evaluation.WEIGHTS`) if you
  want to tune them before the demo.
