# AI-Powered Variant Literature Assistant

An AI-powered application that helps researchers explore scientific literature associated with genetic variants and organize findings into ACMG-oriented evidence summaries.

## Overview

Interpreting genetic variants requires reviewing scientific publications, identifying relevant findings, and evaluating evidence. This project aims to simplify that process by combining biomedical literature retrieval, evidence ranking, and Large Language Models (LLMs).

Users can enter a gene and genetic variant to retrieve relevant research papers, examine extracted evidence, and generate a structured analysis.

## Key Features

- **Gene and Variant Input:** Accepts gene symbols and HGVS-style variant descriptions.
- **Gene Validation:** Uses NCBI resources to retrieve gene information.
- **Variant Processing:** Retrieves variant representations and aliases using ClinVar.
- **Literature Retrieval:** Searches PubMed using NCBI E-utilities.
- **Evidence Ranking:** Ranks retrieved papers using relevance, publication details, and study-related criteria.
- **AI-Based Evidence Extraction:** Uses LLMs to identify potentially relevant ACMG evidence from research abstracts.
- **ACMG-Oriented Reports:** Organizes extracted findings into structured summaries.
- **RAG Chat Assistant:** Allows users to ask questions using retrieved evidence and stored information.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLite |
| Database Integration | SQLAlchemy, pgvector |
| Biomedical Data | NCBI Gene, ClinVar, PubMed |
| AI / LLM | OpenAI, Anthropic |
| Deployment | Docker, Docker Compose |

## System Architecture

1. The user enters a gene and variant through the frontend.
2. The FastAPI backend processes the request.
3. NCBI Gene is used to retrieve gene information.
4. ClinVar is queried for variant representations.
5. PubMed is searched to retrieve relevant publications.
6. Retrieved papers are ranked based on relevance.
7. An LLM extracts potentially relevant evidence from the available literature.
8. The results are stored and organized in the database.
9. The application generates an ACMG-oriented report and supports evidence-based question answering through the chat assistant.

## Project Structure

```text
gene-variant-literature-assistant/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── backend/
│   ├── services/
│   │   ├── variant_processing.py
│   │   ├── pubmed_retrieval.py
│   │   ├── evidence_ranking.py
│   │   ├── evidence_extraction.py
│   │   └── llm_service.py
│   ├── main.py
│   ├── database.py
│   ├── requirements.txt
│   └── Dockerfile
│
└── docker-compose.yml
```

## Running the Project

### Prerequisites

- Python 3.10+
- Node.js and npm
- Docker Desktop (for Docker-based setup)
- API keys for the supported LLM providers, where required

### Option 1: Run with Docker

From the project root:

1. Create a `.env` file and add the API keys you intend to use:

```env
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GEMINI_API_KEY=your_gemini_api_key
```

2. Start the application:

```bash
docker compose up --build
```

3. Open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API documentation: http://localhost:8000/docs

### Option 2: Run Frontend and Backend Separately

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

Configure the backend URL and database connection according to your local environment.

## Future Improvements

- Improved variant normalization and literature matching.
- Retrieval of full-text publications where available.
- More comprehensive evidence extraction and validation.
- Improved semantic search and ranking.
- Enhanced ACMG evidence assessment and report generation
