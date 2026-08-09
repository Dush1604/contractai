# ContractAI

AI-powered contractor intake and estimation platform. Homeowners submit renovation requests — with photos — through a simple public form. Contractors get an AI-generated project classification, follow-up questions, a scope of work, and a cost estimate, all backed by a custom-trained computer vision model and an LLM reasoning layer.

Built as a full-stack, security-hardened, multi-tenant application: FastAPI + PostgreSQL backend, Next.js frontend, a PyTorch image classifier trained from scratch on a curated dataset, and OpenAI-powered analysis/estimation — fully containerized with Docker Compose.

## Demo

*(screenshots / demo video go here)*

## Core workflow

1. Homeowner submits a project request (title, description, photos, contact info) via a public intake form — no account required.
2. Uploaded photos are validated (magic-byte MIME checking, re-encoded, EXIF-stripped) and automatically classified by a custom-trained PyTorch model into one of 8 project categories.
3. A contractor logs into their dashboard and sees the new lead, including the vision model's category prediction.
4. On demand, the contractor triggers AI analysis: an LLM generates a category/complexity assessment, missing-information flags, homeowner-facing follow-up questions, and a scope of work — using both the written description *and* the vision model's prediction as cross-checked inputs.
5. The contractor generates a cost estimate: a dollar range, confidence level, assumptions, and risk factors.
6. The contractor exports a professional PDF estimate report, or the homeowner checks status via a private, token-based link.

## Tech stack

**Frontend:** Next.js (App Router), TypeScript, TailwindCSS
**Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis
**Machine Learning:** PyTorch (ResNet-18, transfer learning), scikit-learn
**AI:** OpenAI API (GPT-4o) for structured reasoning tasks
**Infra:** Docker, Docker Compose, Git LFS (model weights)

## Machine learning: image classifier

A ResNet-18 model, fine-tuned via transfer learning (frozen early layers, unfrozen final residual block + a new classification head with dropout) on a curated dataset of 1,600 images across 8 categories (Deck, Fence, Roofing, Flooring, Drywall, Landscaping, Kitchen, Bathroom), sourced from Unsplash/Pexels under commercial-use-safe licenses.

**Final validation accuracy: 85.3%**, with no category below 0.79 F1.

| Category | Precision | Recall | F1 |
|---|---|---|---|
| Bathroom | 0.867 | 0.796 | 0.830 |
| Deck | 0.935 | 0.690 | 0.795 |
| Drywall | 0.863 | 0.936 | 0.898 |
| Fence | 0.848 | 0.907 | 0.876 |
| Flooring | 0.842 | 0.865 | 0.853 |
| Kitchen | 0.763 | 0.853 | 0.806 |
| Landscaping | 0.829 | 0.919 | 0.872 |
| Roofing | 0.900 | 0.871 | 0.885 |

This model went through three real training iterations, each driven by a specific diagnosed problem rather than blind hyperparameter tweaking:
- **v1 (baseline, 80.6% acc.):** initial dataset, no regularization beyond standard augmentation.
- **v2 (86.6% acc.):** manual inspection revealed the `drywall` category was mostly generic, mislabeled interior photos (stock search results skew toward finished rooms, not mid-installation drywall work) — re-sourced with targeted queries, F1 rose from 0.676 → 0.887. Added dropout + a learning-rate scheduler to address a visible overfitting pattern (near-zero training loss with plateaued validation accuracy).
- **v3 (85.3% acc., final):** `deck` was found to overlap significantly with `landscaping` (broadened search queries had pulled in general backyard scenes) — iterated on search queries twice more (once overcorrecting to context-free wood-texture closeups) before landing on queries anchored to the deck as a structure. Deck's F1 rose from 0.648 → 0.795.

## Security

Built with an "industry-standard by default" posture, not retrofitted:

- Rate limiting (Redis-backed, per-route limits — stricter on auth/intake endpoints)
- Account lockout after repeated failed logins, independent of rate limiting
- JWT auth via httpOnly, SameSite=strict cookies — never exposed to client-side JS
- Bcrypt password hashing
- Strict Pydantic input validation on every endpoint (`extra="forbid"`)
- Upload validation: magic-byte MIME detection (not client-supplied headers), size caps, re-encoding to strip EXIF/malicious payloads, randomized storage filenames
- Multi-tenancy enforced at the query level — every contractor-scoped endpoint filters by the authenticated contractor's own ID, never a client-supplied parameter
- Homeowner access via single-purpose, cryptographically random, expiring claim tokens — no homeowner accounts/passwords to compromise
- CORS locked to a known origin, trusted-host enforcement, full security header set (CSP, HSTS, X-Frame-Options, etc.)
- Secrets via environment variables only; never committed
- Audit logging of authentication events

## Architecture
contractai/
├── backend/ FastAPI app
│ ├── app/api/ Route handlers
│ ├── app/services/ Business logic (DB writes, orchestration)
│ ├── app/ai/ LLM prompt construction + OpenAI calls
│ ├── app/ml/ PyTorch inference wrapper + trained model artifacts
│ ├── app/models/ SQLAlchemy models
│ └── app/db/ Session, Alembic migrations
├── frontend/ Next.js app (homeowner intake + contractor dashboard)
├── ml/ Offline training pipeline (dataset scripts, train.py)
└── docker-compose.yml

Key design decision: the vision classifier and the LLM are deliberately separate, composable systems, not one blended vision-LLM call. The classifier is fast and free per-inference; its output is fed into the LLM's prompt as one structured, explicitly-imperfect signal ("treat as a cross-check, not ground truth") rather than trusted blindly — this keeps runtime AI cost low while still giving the LLM real visual grounding when the homeowner's text description is sparse.

## Local setup

```bash
git clone <repo-url>
cd contractai
git lfs pull  # required — pulls the trained model weights

cp .env.example .env   # fill in real values (JWT secret, OpenAI key, DB credentials)

docker-compose up --build

# first run only: initialize the database
docker-compose exec backend alembic upgrade head

# register a contractor account
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "a-strong-password-12+chars"}'
```

Frontend: `http://localhost:3000` · Backend: `http://localhost:8001` · API docs: `http://localhost:8001/docs`

**Known local-dev limitation:** the intake form's target contractor ID is currently hardcoded in `frontend/src/app/page.tsx` for demo purposes — see Roadmap.

## Roadmap

**Near-term, architecturally straightforward extensions:**
- Instant SMS/email lead acknowledgment on intake submission (the highest-evidence lever in the home-services industry — response speed within minutes vs. hours is documented to produce dramatically higher lead conversion)
- Automated review-request messaging triggered on project completion
- Vision-LLM-based condition assessment (damage/wear analysis from photos) feeding directly into estimate risk factors — deliberately deferred; the current classifier/LLM separation makes this a clean addition, not a rewrite

**Productization path:**
- Currently architected as one deployment per contractor (embeddable via iframe on the contractor's existing site). A central multi-tenant SaaS model was considered and explicitly deferred — see design notes on `contractor_id`-based tenancy, per-tenant CORS, and per-tenant rate limiting as the required changes if that model is pursued later.
- GBP/local-SEO health-check tooling as a lead-generation tool for a productized-agency go-to-market.

## License

This project is source-available for portfolio and educational review. 
All rights reserved — please contact me before reusing any part of this 
code commercially.