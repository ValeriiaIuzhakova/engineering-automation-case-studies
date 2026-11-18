# Engineering Automation Case Studies

Write-ups of automations I designed and built to improve engineering operations at a B2B SaaS
company. Each one covers the problem, my contribution, the design, the safeguards, what it did and
didn't achieve, and what I'd change.

| Case study | Status | What it shows |
|---|---|---|
| [AI Bug Classification Pipeline](ai-bug-classification/) | In production | LLM classification with strict validation, confidence-tiered human review, audit logging, and a post-rollout audit that changed the design |
| Incident Follow-Up Tracking | Write-up in progress | Agentic Claude Code skills with human approval before any ticket is created, safe re-runs, and a backoff reminder cadence |

The code in each `examples/` folder is a small, independently written illustration using synthetic
data. It is not production code. See the disclosure note in each case study.
