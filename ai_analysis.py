"""
ai_analysis.py
Local, dependency-free "AI" layer for idea analysis.

No external LLM API key is required (works fully offline), which satisfies the
"local fallback if external AI API is unavailable" requirement -- here it IS
the primary engine. Techniques used are classic NLP / IR, implemented with
plain Python + NumPy:
  - keyword-weighted category classification
  - word-frequency extractive summarization
  - keyword-cue problem-sentence extraction
  - template-driven improvement / requirement / implementation suggestions
"""

import re
import numpy as np

STOPWORDS = set("""
a an the is are was were be been being of to in on for with and or but if
this that these those it its our your their his her they them we you i
as at by from into over under about after before because so such not no
can will would should could may might do does did have has had will
""".split())

CATEGORY_KEYWORDS = {
    "Process Improvement": ["process", "workflow", "manual", "delay", "approval", "paperwork", "bottleneck", "efficiency"],
    "Cost Reduction": ["cost", "expense", "budget", "save", "saving", "waste", "cheaper", "reduce spend"],
    "Technology & Automation": ["automation", "software", "app", "ai", "machine learning", "system", "digital", "bot", "algorithm", "sensor", "iot"],
    "Customer Experience": ["customer", "client", "user experience", "service", "satisfaction", "feedback", "support"],
    "Sustainability": ["energy", "waste", "recycle", "green", "carbon", "sustainable", "environment", "solar"],
    "Product Innovation": ["product", "feature", "design", "prototype", "innovation", "new product"],
    "Workplace & HR": ["employee", "hr", "training", "workplace", "culture", "onboarding", "wellbeing", "safety"],
    "Safety & Risk": ["safety", "hazard", "risk", "accident", "compliance", "monitoring", "alert", "warning"],
}

REQUIREMENTS_BY_CATEGORY = {
    "Process Improvement": ["Process mapping of current workflow", "Stakeholder sign-off from affected departments", "Pilot rollout plan"],
    "Cost Reduction": ["Cost-benefit analysis", "Finance team approval", "Baseline cost data for comparison"],
    "Technology & Automation": ["Technical feasibility study", "IT infrastructure / cloud resources", "Data privacy & security review"],
    "Customer Experience": ["Customer feedback data", "UX/UI design review", "Support team training"],
    "Sustainability": ["Environmental impact assessment", "Compliance with sustainability standards", "Vendor/material sourcing plan"],
    "Product Innovation": ["Prototype / MVP", "Market research", "R&D budget allocation"],
    "Workplace & HR": ["HR policy alignment", "Employee training plan", "Change management communication"],
    "Safety & Risk": ["Risk assessment report", "Safety compliance certification", "Monitoring equipment / tools"],
}

PROBLEM_CUES = [
    "problem", "issue", "challenge", "difficult", "delay", "waste", "inefficient",
    "manual", "error", "lack of", "unable", "slow", "costly", "risk", "fail",
]

IMPROVEMENT_TEMPLATES = [
    "Introduce a structured {focus} workflow to remove the manual/ad-hoc steps described.",
    "Add measurable KPIs to track {focus} before and after rollout.",
    "Pilot the idea in one department before a company-wide rollout to de-risk {focus}.",
    "Use automation/AI where possible to reduce human effort in {focus}.",
]


def _tokenize(text):
    text = str(text).lower()
    words = re.findall(r"[a-z']+", text)
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def _sentences(text):
    text = str(text).strip()
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def categorize(title, description, hint_category=""):
    """Keyword-weighted classification. Falls back to the user-picked category."""
    text = f"{title} {description}".lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(text.count(kw) for kw in keywords)
        if score:
            scores[cat] = score
    if not scores:
        return hint_category or "General / Uncategorized"
    best = max(scores, key=scores.get)
    return best


def summarize(text, max_sentences=2):
    """Word-frequency extractive summarization (NumPy-scored)."""
    sents = _sentences(text)
    if len(sents) <= max_sentences:
        return text.strip()

    words = _tokenize(text)
    if not words:
        return " ".join(sents[:max_sentences])

    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    max_f = max(freq.values())
    for w in freq:
        freq[w] = freq[w] / max_f

    sent_scores = np.zeros(len(sents))
    for i, s in enumerate(sents):
        s_words = _tokenize(s)
        if not s_words:
            continue
        sent_scores[i] = sum(freq.get(w, 0) for w in s_words) / len(s_words)

    top_idx = sorted(np.argsort(sent_scores)[-max_sentences:])
    return " ".join(sents[i] for i in top_idx)


def identify_problem(text):
    sents = _sentences(text)
    for s in sents:
        low = s.lower()
        if any(cue in low for cue in PROBLEM_CUES):
            return s
    return sents[0] if sents else "No explicit problem statement detected -- consider clarifying the pain point."


def suggest_improvements(text, category):
    focus = category.lower() if category else "the proposed process"
    picks = IMPROVEMENT_TEMPLATES[:3]
    return " ".join(t.format(focus=focus) for t in picks)


def suggest_requirements(category):
    reqs = REQUIREMENTS_BY_CATEGORY.get(category, ["Feasibility study", "Budget approval", "Stakeholder buy-in"])
    return "; ".join(reqs)


def suggest_implementation_plan(category, cost):
    try:
        cost_val = float(cost)
    except (TypeError, ValueError):
        cost_val = 0
    if cost_val <= 25000:
        tier = "Low-cost / fast-track"
        steps = "1) Assign a single-owner pilot team. 2) Implement within the current sprint/cycle. 3) Review impact after 2-4 weeks."
    elif cost_val <= 150000:
        tier = "Medium investment"
        steps = "1) Form a cross-functional task force. 2) Run a 4-6 week pilot in one department. 3) Evaluate ROI before full rollout."
    else:
        tier = "Major investment"
        steps = "1) Present business case to leadership for budget approval. 2) Run a phased 3-month pilot with clear success metrics. 3) Full rollout only after pilot validation."
    return f"[{tier}] {steps} (Category focus: {category})"


def analyze_idea(title, description, department, hint_category, cost):
    """Run the full AI analysis pipeline and return a dict ready to store."""
    category = categorize(title, description, hint_category)
    summary = summarize(description)
    problem = identify_problem(description)
    improvements = suggest_improvements(description, category)
    requirements = suggest_requirements(category)
    implementation = suggest_implementation_plan(category, cost)
    return {
        "ai_category": category,
        "ai_summary": summary,
        "ai_problem": problem,
        "ai_improvements": improvements,
        "ai_requirements": requirements,
        "ai_implementation": implementation,
    }
