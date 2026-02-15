# Kudi Ecosystem

**A Financial Intelligence Ecosystem for Nigerian Tax Management**

KudiWise helps individuals, freelancers, and SMEs understand Nigerian taxes, calculate obligations, and stay compliant — powered by AI and the Nigeria Tax Act 2025.

## Architecture

```
kudi-ecosystem/
├── backend/          # FastAPI + KudiCore engine + AI assistant
├── frontend/         # Next.js 14 + shadcn/ui dashboard
└── docker-compose.yml
```

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy |
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui |
| Database | Supabase (PostgreSQL + pgvector + Auth + Storage) |
| AI/RAG | LlamaIndex, Groq (Llama 3.1 70B), sentence-transformers |
| Payments | Paystack (NGN) + Stripe (international) |
| Cache | Redis |

### KudiCore Engine

Deterministic tax calculators based on the Nigeria Tax Act 2025:

- **PIT** — Personal Income Tax (Section 58, Fourth Schedule)
- **CIT** — Company Income Tax (Section 56: 0% small, 30% standard)
- **VAT** — Value Added Tax (Section 148: 7.5%)
- **WHT** — Withholding Tax (varies by payment/recipient type)
- **Currency** — Multi-currency conversion via CBN official rates
- **Classifier** — Transaction classification (income/expense/capital)
- **Anomaly** — Missed deductions, deadline alerts, audit triggers
- **Scenario** — "What-if" tax modeling

### AI Tax Assistant

Hybrid architecture:
1. **RAG** — Retrieves relevant sections from the Nigeria Tax Act 2025
2. **Tool Calling** — Invokes KudiCore calculators during conversation
3. **Prompt Engineering** — Nigerian tax expert persona with legal disclaimers

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Supabase account
- Groq API key

### Backend

```bash
cd backend
cp .env.example .env    # Fill in your keys
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local    # Fill in your keys
npm install
npm run dev
```

### Run Tests

```bash
cd backend
pytest tests/ -v
```

### Docker

```bash
docker-compose up --build
```

### Database Setup

Run the migration SQL in your Supabase SQL Editor:

```sql
-- Copy contents of backend/supabase/migrations/001_initial_schema.sql
-- into the Supabase SQL Editor and execute
```

This creates all tables, enums, RLS policies, pgvector indexes, and auto-triggers.

### Ingest Tax Documents (RAG)

```bash
cd backend
pip install PyMuPDF sentence-transformers
python -m scripts.ingest_documents \
  --file /path/to/Nigeria-Tax-Act-2025.pdf \
  --name "Nigeria Tax Act 2025"
```

This chunks the PDF, generates embeddings (384-dim via MiniLM-L6-v2), and uploads to the `document_embeddings` table in Supabase for RAG retrieval.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon key |
| `GROQ_API_KEY` | Groq API key for LLM inference |
| `PAYSTACK_SECRET_KEY` | Paystack secret key |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `REDIS_URL` | Redis connection URL |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |
| `NEXT_PUBLIC_API_URL` | Backend API URL |

## Tax Rates (Nigeria Tax Act 2025)

### PIT Brackets (Fourth Schedule)
| Taxable Income | Rate |
|---------------|------|
| First ₦800,000 | 0% |
| Next ₦2,200,000 | 15% |
| Next ₦9,000,000 | 18% |
| Next ₦13,000,000 | 21% |
| Next ₦25,000,000 | 23% |
| Above ₦50,000,000 | 25% |

### CIT (Section 56)
- Small companies (turnover ≤ ₦25M): **0%**
- All other companies: **30%**
- Development Levy: **4%** (non-small companies)

### VAT (Section 148)
- Standard rate: **7.5%**

## Disclaimer

This software is for **educational and informational purposes only**. It does not constitute professional tax, legal, or financial advice. Always consult a qualified tax professional or FIRS for advice specific to your situation.

## License

Proprietary — All rights reserved.
