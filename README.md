# SGTE — Smart Guided Troubleshooting Engine

<p align="center">
  <strong>AI-Assisted Device Troubleshooting & Guided Resolution</strong>
</p>

<p align="center">
  Convert natural-language device complaints into structured troubleshooting guidance.
</p>

---

## Overview

**SGTE (Smart Guided Troubleshooting Engine)** is an AI-assisted troubleshooting platform designed to help users move from an informal device complaint to a structured, actionable troubleshooting plan.

Instead of requiring users to identify the exact technical issue or manually search through support documentation, SGTE accepts complaints in everyday language and processes them through a modular troubleshooting pipeline.

### Example

**User input**

> "My phone screen keeps flickering and sometimes turns black."

**SGTE**

```text
User Complaint
      ↓
Query Understanding
      ↓
Information Retrieval
      ↓
Troubleshooting Plan
      ↓
Action / Navigation Mapping
      ↓
Structured Response
````

The project combines:

* Natural-language query understanding
* Query enrichment
* Hybrid retrieval
* Semantic caching
* Structured troubleshooting
* Deep-link mapping
* Response validation
* REST API delivery
* React-based user interface

---

# Problem

Device troubleshooting is often difficult because users describe problems differently from how technical documentation describes them.

For example:

> "My screen is acting weird and goes black randomly."

A troubleshooting system needs to understand concepts such as:

* Display issues
* Screen flickering
* Black screen
* Device settings
* Display-related troubleshooting actions

Traditional search-based approaches can require users to already know the correct technical terminology.

**SGTE aims to bridge this gap by transforming informal device complaints into structured troubleshooting workflows.**

---

# Key Features

## 🧠 Natural-Language Query Understanding

SGTE accepts everyday descriptions instead of requiring users to enter predefined technical keywords.

The query-processing layer performs:

* Query normalization
* Query enrichment
* Intent identification
* Query variation generation
* Symptom and action understanding

---

## 🔎 Hybrid Retrieval

SGTE combines multiple retrieval strategies to improve matching between user complaints and available troubleshooting information.

The retrieval pipeline includes:

* Dense retrieval
* TF-IDF / lexical retrieval
* Query enrichment
* Semantic matching
* Reranking

This allows the system to handle different ways of describing similar device problems.

---

## ⚡ Semantic Caching

SGTE includes a semantic caching layer for repeated or semantically similar troubleshooting queries.

The cache can reuse previously available troubleshooting plans instead of repeatedly executing the full processing pipeline.

This is intended to:

* Reduce repeated processing
* Improve response time for repeated queries
* Avoid unnecessary model calls where an appropriate cached result exists

---

## 🧩 Structured Troubleshooting Plans

Instead of returning an unstructured paragraph, SGTE produces a structured troubleshooting response.

The response can contain:

* Troubleshooting actions
* Action descriptions
* Supporting information
* Navigation information
* Evidence metadata
* Fallback information where applicable

The backend also uses validation and output contracts to keep responses consistent.

---

## 📱 Guided Device Navigation

Where an appropriate entry exists in the available deep-link catalogue, troubleshooting actions can be associated with device Settings navigation information.

This allows troubleshooting to move beyond:

> "Go to Settings."

toward:

> "Open the relevant Settings destination and perform the required action."

Navigation mapping is performed using the available catalogue rather than arbitrary external URLs.

---

## 🛡️ Validation & Controlled Output

The backend contains validation mechanisms for:

* Response structure
* Evidence metadata
* Deep-link mapping
* Action information
* URL leakage
* Fallback behaviour

The objective is to prevent unsupported or malformed information from being presented as a troubleshooting result.

---

# System Architecture

```text
                    ┌──────────────────────┐
                    │    User Complaint    │
                    │ Natural-language     │
                    │ device problem       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Query Enrichment    │
                    │ Normalization +      │
                    │ Query Understanding  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Semantic Cache     │
                    │    Fast-path lookup  │
                    └───────┬───────┬──────┘
                            │       │
                       Cache Hit    │ Cache Miss
                            │       │
                            │       ▼
                            │ ┌──────────────────────┐
                            │ │ Structure Extraction │
                            │ │ Intent + Actions     │
                            │ └──────────┬───────────┘
                            │            │
                            │            ▼
                            │ ┌──────────────────────┐
                            │ │ Retrieval & Mapping  │
                            │ │ SIIS + Hybrid        │
                            │ │ Retrieval + Deeplinks│
                            │ └──────────┬───────────┘
                            │            │
                            │            ▼
                            │ ┌──────────────────────┐
                            │ │      Validation      │
                            │ │    Output Contract   │
                            │ └──────────┬───────────┘
                            │            │
                            └─────┬──────┘
                                  ▼
                    ┌──────────────────────┐
                    │   FastAPI REST API   │
                    │   Structured JSON    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     React / Vite     │
                    │  Troubleshooting UI  │
                    └──────────────────────┘
```

---

# Getting Started

Follow the steps below to run SGTE locally.

## Prerequisites

Install the following before starting:

* Python 3.10+
* Node.js 18+
* npm
* Git

Verify the installations:

```bash
python --version
node --version
npm --version
git --version
```

---

# 1. Clone the Repository

```bash
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPOSITORY>.git
cd Smart_Guided_TroubleShoot
```

Replace `<YOUR_USERNAME>` and `<YOUR_REPOSITORY>` with your GitHub repository details.

---

# 2. Set Up the Backend

SGTE uses **Python + FastAPI** for its backend.

## Create a Virtual Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## Install Backend Dependencies

From the project root:

```bash
pip install -r requirements.txt
```

---

# 3. Configure Environment Variables

A template environment file is included:

```text
.env.example
```

Create your local `.env` file from the template.

### Windows

```powershell
Copy-Item .env.example .env
```

### macOS / Linux

```bash
cp .env.example .env
```

Open `.env` and configure the required provider settings.

> **Important:** Never commit API keys, credentials, or other secrets to GitHub.
>
> The `.env` file is ignored by Git. Only `.env.example` should be committed.

---

# 4. Run the Backend

Make sure the Python virtual environment is activated.

From the project root:

```bash
uvicorn sgte.api:app --reload
```

The backend will start at:

```text
http://127.0.0.1:8000
```

---

## Backend Health Check

Open:

```text
http://127.0.0.1:8000/health
```

You can also check it using:

```bash
curl http://127.0.0.1:8000/health
```

A successful response confirms that the SGTE backend is running.

---

# 5. Run the Frontend

Keep the backend terminal running.

Open a **second terminal** and navigate to the frontend:

```bash
cd frontend
```

Install frontend dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Vite will display a local URL similar to:

```text
http://localhost:5173
```

Open the URL shown in the terminal in your browser.

---

# 6. Use the Application

Once both the backend and frontend are running:

1. Open the SGTE web interface.
2. Enter a device complaint in natural language.
3. Submit the complaint.
4. SGTE processes the query through the troubleshooting pipeline.
5. Review the generated troubleshooting plan.
6. Follow the recommended actions.
7. Use available Settings navigation links when provided.

---

## Example Queries

Try queries such as:

```text
My phone screen keeps flickering and sometimes turns black.
```

```text
My phone keeps disconnecting from Wi-Fi when the screen turns off.
```

```text
My phone is getting hot and the battery is draining quickly.
```

```text
The camera becomes slow when I try to take pictures.
```

The exact response depends on the available knowledge, retrieval results, configuration, and execution mode.

---

# 7. Run the Test Suite

SGTE includes an automated backend test suite.

From the **project root**:

```bash
pytest
```

For detailed output:

```bash
pytest -v
```

The tests cover areas including:

* Semantic cache behaviour
* Cache prewarming
* Query variations
* Intent detection
* Lexical precision
* Deep-link mapping
* LLM provider integrations
* Fallback behaviour
* Output contracts
* Evidence handling
* Validation
* Polarity and negation handling
* Repository and loader behaviour

---

# 8. Build the Frontend

To verify that the frontend builds successfully:

```bash
cd frontend
npm run build
```

The production build will be generated by Vite.

---

# 9. REST API

SGTE exposes a REST API through FastAPI.

## Health Check

```http
GET /health
```

Example:

```bash
curl http://127.0.0.1:8000/health
```

---

## Troubleshooting Endpoint

```http
POST /v1/troubleshoot
```

Example request:

```json
{
  "query": "My phone screen keeps flickering and turning black."
}
```

The endpoint returns a structured troubleshooting response.

For detailed API documentation, see:

* [`docs/API.md`](docs/API.md)
* [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md)
* [`docs/VALIDATION_RULES.md`](docs/VALIDATION_RULES.md)

---

# 10. Offline / MOCK Mode

SGTE includes an offline demonstration mode using the mock LLM provider.

This allows the application to be demonstrated without requiring a live external LLM provider.

The application indicates when it is running in **MOCK** mode.

> **Note:** MOCK mode is intended for development and demonstration. It should not be interpreted as a live-provider accuracy evaluation.

Additional information:

* [`docs/offline_demo.md`](docs/offline_demo.md)
* [`docs/demo_guide.md`](docs/demo_guide.md)
* [`docs/demo_checklist.md`](docs/demo_checklist.md)
* [`docs/live_provider_setup.md`](docs/live_provider_setup.md)

---

# Quick Start

If Python, Node.js, npm, and Git are already installed:

## Terminal 1 — Backend

```bash
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPOSITORY>.git
cd Smart_Guided_TroubleShoot

python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create environment file

```powershell
Copy-Item .env.example .env
```

### Start backend

```bash
uvicorn sgte.api:app --reload
```

---

## Terminal 2 — Frontend

Open a new terminal:

```bash
cd Smart_Guided_TroubleShoot\frontend
npm install
npm run dev
```

Then open the local URL shown by Vite.

---

# Troubleshooting Setup Issues

## Python command not found

Verify that Python is installed:

```bash
python --version
```

If your system uses `python3`, try:

```bash
python3 --version
```

---

## Node or npm command not found

Verify Node.js and npm:

```bash
node --version
npm --version
```

Install Node.js if either command is unavailable.

---

## Backend dependencies are missing

Make sure the virtual environment is activated and run:

```bash
pip install -r requirements.txt
```

---

## Frontend dependencies are missing

From the `frontend` directory:

```bash
npm install
```

---

## Port 8000 is already in use

Run FastAPI on another port:

```bash
uvicorn sgte.api:app --reload --port 8001
```

If the frontend is configured to use a specific backend URL, update the corresponding configuration accordingly.

---

# Technology Stack

| Layer           | Technology                                  |
| --------------- | ------------------------------------------- |
| Frontend        | React.js, TypeScript, Vite                  |
| Backend         | Python, FastAPI                             |
| Data Validation | Pydantic                                    |
| AI / LLM        | Configurable LLM Providers                  |
| Retrieval       | Dense Retrieval, TF-IDF / Lexical Retrieval |
| Knowledge       | SIIS Knowledge Resources                    |
| Navigation      | Device Settings Deep-Link Catalogue         |
| Testing         | Pytest                                      |
| Version Control | Git, GitHub                                 |

---

# Project Structure

```text
Smart_Guided_TroubleShoot/
│
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       ├── types/
│       ├── App.tsx
│       ├── index.css
│       └── main.tsx
│
├── sgte/
│   ├── cache/
│   │   ├── prewarm.py
│   │   └── semantic.py
│   │
│   ├── embeddings/
│   │   ├── base.py
│   │   ├── dense.py
│   │   └── tfidf.py
│   │
│   ├── llm/
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── gemini_provider.py
│   │   ├── groq_provider.py
│   │   ├── openai_provider.py
│   │   └── mock.py
│   │
│   ├── query/
│   │   ├── canonical.py
│   │   ├── enrich.py
│   │   ├── normalize.py
│   │   └── understand.py
│   │
│   ├── api.py
│   ├── builder.py
│   ├── deeplink_repo.py
│   ├── engine.py
│   ├── evidence.py
│   ├── extractor.py
│   ├── hybrid_mapper.py
│   ├── intent.py
│   ├── lexical.py
│   ├── loaders.py
│   ├── pipeline.py
│   ├── settings.py
│   ├── siis_repo.py
│   └── validator.py
│
├── tests/
│   ├── conftest.py
│   ├── test_cache_prewarm.py
│   ├── test_confidence_head_evidence.py
│   ├── test_deeplink_mapper_scoped_fixes.py
│   ├── test_fallback_metadata.py
│   ├── test_gemini_provider.py
│   ├── test_groq_provider.py
│   ├── test_intent_primary_operation.py
│   ├── test_loaders_and_repos.py
│   ├── test_output_contract.py
│   ├── test_query_variations.py
│   ├── test_validator.py
│   └── ...
│
├── docs/
│   ├── API.md
│   ├── DATA_CONTRACT.md
│   ├── VALIDATION_RULES.md
│   ├── demo_guide.md
│   ├── demo_checklist.md
│   ├── live_provider_setup.md
│   └── offline_demo.md
│
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

---

# Design Principles

## 1. Evidence-Aware Troubleshooting

Troubleshooting guidance should be based on available knowledge and retrieval results rather than inventing unsupported steps.

## 2. Structured Responses

The backend produces structured responses instead of relying entirely on free-form text.

## 3. Modular Architecture

Query understanding, retrieval, caching, mapping, validation, and API handling are separated into reusable modules.

## 4. Controlled Navigation

Device navigation is mapped through the available deep-link catalogue rather than treating arbitrary URLs as valid device navigation.

## 5. Graceful Fallbacks

When sufficient information is unavailable, the system can return controlled fallback responses instead of presenting unsupported troubleshooting information as certain.

---

# Current Prototype Status

SGTE is currently a **functional prototype / hackathon implementation**.

The repository contains:

* React frontend
* FastAPI backend
* Query-processing pipeline
* Retrieval components
* Semantic caching
* Deep-link mapping
* Validation
* Multiple LLM provider integrations
* Automated tests
* API documentation
* Demo documentation

The current demo can operate in **MOCK mode** for offline demonstration.

Live-provider execution and production deployment require additional configuration and validation.

---

# Known Limitations

The current prototype has areas that can be improved further:

* Troubleshooting coverage can be expanded.
* Retrieval relevance can be improved for complex or multi-symptom complaints.
* Device navigation coverage depends on the available catalogue.
* Some complex queries may require more specialized knowledge.
* Production deployment requires further provider validation and operational hardening.
* Broader representative evaluation is required before making production-level accuracy claims.

---

# Future Improvements

## 🔹 Expanded Knowledge Coverage

Increase the number of supported troubleshooting scenarios and device categories.

## 🔹 Improved Retrieval

Improve semantic and lexical retrieval for complex, ambiguous, and multi-symptom complaints.

## 🔹 Better Navigation Coverage

Expand verified device Settings navigation mappings.

## 🔹 Evaluation Framework

Introduce broader representative datasets and evaluation metrics for:

* Retrieval relevance
* Step accuracy
* Deep-link accuracy
* Response latency
* Cache effectiveness
* Cost per query

## 🔹 Production Readiness

Complete live-provider validation, deployment configuration, monitoring, and operational safeguards.

---

# Documentation

Additional project documentation is available in the `docs/` directory.

| Document                                                  | Description                  |
| --------------------------------------------------------- | ---------------------------- |
| [`API.md`](docs/API.md)                                   | REST API details             |
| [`DATA_CONTRACT.md`](docs/DATA_CONTRACT.md)               | Structured response contract |
| [`VALIDATION_RULES.md`](docs/VALIDATION_RULES.md)         | Validation behaviour         |
| [`demo_guide.md`](docs/demo_guide.md)                     | Demo walkthrough             |
| [`demo_checklist.md`](docs/demo_checklist.md)             | Demo checklist               |
| [`demo_results_summary.md`](docs/demo_results_summary.md) | Demo results summary         |
| [`live_provider_setup.md`](docs/live_provider_setup.md)   | Live provider configuration  |
| [`offline_demo.md`](docs/offline_demo.md)                 | Offline / MOCK mode          |

---

# Development Workflow

```text
User Complaint
      ↓
Query Enrichment
      ↓
Semantic Cache
      ↓
Query Understanding
      ↓
Retrieval
      ↓
Action / Deep-Link Mapping
      ↓
Validation
      ↓
Structured API Response
      ↓
React UI
```

Each major stage is implemented as a separate module so that individual components can be tested and improved independently.

---

# Contributing

This repository was developed as a hackathon prototype.

For development:

1. Create a feature branch.
2. Make the required changes.
3. Add or update tests.
4. Run the test suite.
5. Verify the frontend build.
6. Commit the changes.

Before committing, ensure that no API keys, credentials, local environment files, or generated artifacts are included.

---

# License

This project was developed as a hackathon prototype.

Add an appropriate license if the project is later released under an open-source license.

---

<p align="center">
  <strong>SGTE</strong><br>
  Smart Guided Troubleshooting Engine
</p>

<p align="center">
  From natural-language complaints to structured guided troubleshooting.
</p>
```