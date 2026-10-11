# AI Document Intelligence Platform 📄🤖

An AI-powered document analysis platform that helps users understand contracts by extracting key information, identifying important clauses, detecting potential risks, and answering questions based on the uploaded document.

## 🚀 Live Demo

- **Frontend:** https://ai-document-intelligence-flame.vercel.app
- **Backend API:** https://ai-document-intelligence-immb.onrender.com
- **API Documentation:** https://ai-document-intelligence-immb.onrender.com/docs

## ✨ Features

- **PDF Upload:** Upload PDF contracts for automated analysis.
- **Document Summarization:** Generate a concise overview of the document.
- **Clause Detection:** Identify important clauses, including liability, payment, and intellectual property.
- **Risk Detection:** Highlight potentially risky contract terms and display a risk score.
- **AI-Powered Q&A:** Ask questions about the uploaded document and receive context-based answers.
- **Web Interface:** Interact with document analysis results through a responsive frontend.

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| AI Integration | Gemini API |
| PDF Processing | Python PDF extraction libraries |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |
| Version Control | Git, GitHub |

## 🏗️ Architecture

```text
User
  |
  v
React + TypeScript Frontend
  |  Vercel
  v
FastAPI Backend
  |  Render
  +--> PDF Text Extraction
  +--> Clause Detection
  +--> Risk Scoring
  +--> Document Summarization
  +--> AI Question Answering
  |
  v
PostgreSQL Database
```

## ⚙️ How It Works

1. Upload a PDF contract through the web interface.
2. The backend extracts text from the document.
3. The application identifies relevant clauses and potential risks.
4. A summary and risk score are displayed.
5. Ask questions about the uploaded contract to receive answers based on the retrieved document context.

## 💻 Run Locally

### Prerequisites

- Python
- Node.js and npm
- PostgreSQL

### 1. Clone the repository

```bash
git clone https://github.com/rithikka01/ai-document-intelligence.git
cd ai-document-intelligence
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows:**

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables in a local `.env` file, including the database connection string and AI API key. Use the variable names expected by your backend configuration.

Start FastAPI:

```bash
uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed in your terminal, usually `http://localhost:5173`.

## 🔐 Environment Variables

Configure secrets through local environment variables and your deployment provider's environment settings.

- Database connection URL
- AI API key
- Frontend backend URL, as required by the Vite configuration

**Never commit API keys, database passwords, or `.env` files containing secrets.**

## 📸 Screenshots

Add screenshots of the following sections to this repository:

- Document upload interface
- Document summary and risk score
- Detected clauses
- AI question-and-answer results

## 🔮 Future Improvements

- More advanced retrieval-augmented generation (RAG)
- Support for additional document formats
- Document history and search
- Exportable analysis reports
- Automated tests and improved error handling

## ⚠️ Disclaimer

This project is intended to assist with document understanding and preliminary contract review. Its output may be incomplete or inaccurate and should not replace professional legal advice.

## 👩‍💻 Author

**Rithikka N.**

- GitHub: https://github.com/rithikka01
- LinkedIn: https://www.linkedin.com/in/rithikka-n-7018a2257/

---

Built with Python, FastAPI, React, TypeScript, PostgreSQL, and AI.
