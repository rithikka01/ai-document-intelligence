# AI Document Intelligence Platform

An AI-powered contract analysis platform that helps users understand legal documents by identifying important clauses, detecting potential risks, summarizing contracts, and answering questions using Retrieval-Augmented Generation (RAG).

## Features

- **PDF Document Analysis:** Upload PDF contracts and extract their text.
- **Clause Detection:** Identify clauses such as liability, payment, and intellectual property.
- **Risk Detection:** Highlight potentially risky contract terms and generate a risk score.
- **AI-Powered Summarization:** Generate concise summaries of uploaded documents.
- **Ask AI:** Ask questions about a contract and receive context-based answers.
- **Semantic Search:** Retrieve relevant document sections using vector embeddings.

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** React, TypeScript, Vite
- **Database:** PostgreSQL, pgvector
- **AI/LLM:** Ollama, Llama 3.2
- **Embeddings:** all-MiniLM
- **Document Processing:** PyPDF
- **Tools:** Git, GitHub, Docker

## Architecture

1. Upload a contract PDF through the frontend.
2. Extract text and split it into smaller chunks.
3. Generate embeddings and store document chunks in PostgreSQL with pgvector.
4. Analyze clauses and detect potential risks.
5. Retrieve relevant chunks using vector similarity for AI-powered question answering.

## Getting Started

### Prerequisites

- Python
- Node.js and npm
- Docker Desktop
- Ollama with the required models

### Backend

```bash
cd backend
python -m venv venv
```

Activate the virtual environment, install dependencies, and start the API:

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

### Database and AI Models

Start PostgreSQL using Docker Compose and ensure Ollama is running with these models:

```bash
ollama pull llama3.2:3b
ollama pull all-minilm:latest
```

Configure your database connection in the backend environment before running the application.

## Future Improvements

- User authentication and document history
- Contract comparison
- Downloadable analysis reports
- Cloud deployment

## Disclaimer

This platform provides AI-assisted contract analysis for informational purposes only. It does not replace advice from a qualified legal professional.

## Author

**Rithikka N.**

GitHub: [rithikka01](https://github.com/rithikka01)
