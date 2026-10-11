
import re
import json
import urllib.request
from io import BytesIO

import ollama

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader

from sqlalchemy import text
from sqlalchemy.orm import Session

from pgvector.sqlalchemy import Vector

from database import Base, engine, get_db
from models import Document, DocumentChunk



# --------------------------------------------------
# FastAPI setup
# --------------------------------------------------

app = FastAPI(
    title="AI Document Intelligence API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# Temporary document chunks
# --------------------------------------------------

document_chunks = []


# --------------------------------------------------
# Risk detection rules
# --------------------------------------------------

RISK_RULES = [
    {
        "name": "Non-Compete Clause",
        "keywords": [
            "non-compete",
            "non compete",
            "noncompetition"
        ],
        "level": "High",
        "points": 25,
        "explanation":
            "This clause may restrict the party from working with competitors."
    },
    {
        "name": "Termination Clause",
        "keywords": [
            "termination",
            "terminate this agreement",
            "termination of agreement"
        ],
        "level": "Medium",
        "points": 15,
        "explanation":
            "Review termination conditions, notice periods and associated penalties."
    },
    {
        "name": "Liability Clause",
        "keywords": [
            "liability",
            "liable",
            "limitation of liability"
        ],
        "level": "High",
        "points": 20,
        "explanation":
            "This clause may define significant financial or legal responsibility."
    },
    {
        "name": "Indemnity Clause",
        "keywords": [
            "indemnify",
            "indemnification",
            "indemnity"
        ],
        "level": "High",
        "points": 20,
        "explanation":
            "Indemnity obligations can create financial and legal exposure."
    },
    {
        "name": "Confidentiality Clause",
        "keywords": [
            "confidentiality",
            "confidential information",
            "non-disclosure"
        ],
        "level": "Medium",
        "points": 10,
        "explanation":
            "Check what information is confidential and how long the obligation lasts."
    },
    {
        "name": "Payment Clause",
        "keywords": [
            "payment",
            "invoice",
            "fees",
            "compensation"
        ],
        "level": "Low",
        "points": 5,
        "explanation":
            "Review payment terms, deadlines and penalties."
    },
]


# --------------------------------------------------
# PDF text extraction
# --------------------------------------------------

def extract_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n".join(pages).strip()


# --------------------------------------------------


# Text chunking
# --------------------------------------------------

def split_into_chunks(text: str):
    words = text.split()
    chunk_size = 30
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])

        if len(chunk.strip()) > 20:
            chunks.append(chunk.strip())

    return chunks[:100]


def create_embedding(content: str) -> list[float]:
    safe_content = content[:300]

    response = ollama.embeddings(
        model="all-minilm:latest",
        prompt=safe_content
    )

    return response["embedding"]


# --------------------------------------------------
# Risk detection
# --------------------------------------------------

def detect_risks(text: str):
    lower_text = text.lower()

    risks = []
    score = 0

    for rule in RISK_RULES:

        found = any(
            keyword in lower_text
            for keyword in rule["keywords"]
        )

        if found:

            risks.append({
                "clause": rule["name"],
                "level": rule["level"],
                "explanation": rule["explanation"]
            })

            score += rule["points"]

    return risks, min(score, 100)


# --------------------------------------------------
# Clause detection
# --------------------------------------------------

def detect_clauses(text: str):

    lower_text = text.lower()

    clauses = []

    clause_keywords = {

        "Termination": [
            "termination",
            "terminate"
        ],

        "Confidentiality": [
            "confidentiality",
            "confidential information"
        ],

        "Non-Compete": [
            "non-compete",
            "non compete"
        ],

        "Liability": [
            "liability",
            "liable"
        ],

        "Indemnity": [
            "indemnify",
            "indemnification",
            "indemnity"
        ],

        "Payment": [
            "payment",
            "fees",
            "compensation"
        ],

        "Intellectual Property": [
            "intellectual property",
            "copyright",
            "ownership"
        ],
    }

    for name, keywords in clause_keywords.items():

        if any(
            keyword in lower_text
            for keyword in keywords
        ):
            clauses.append(name)

    return clauses


# --------------------------------------------------
# Summary generation
# --------------------------------------------------

def create_summary(risks, clauses, text):

    if not text:
        return "No readable text was extracted from this document."

    if not risks:

        return (
            f"The document contains {len(clauses)} "
            "recognized clause categories. "
            "No major predefined risk patterns were detected."
        )

    risk_names = ", ".join(
        risk["clause"]
        for risk in risks
    )

    return (
        f"The document contains {len(clauses)} "
        f"recognized clause categories. "
        f"Potential risk areas detected: "
        f"{risk_names}. Review these clauses carefully."
    )


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():

    return {
        "message": "AI Document Intelligence API is running"
    }


# --------------------------------------------------

# Analyze document
# --------------------------------------------------

@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    file_bytes = await file.read()
    text = extract_text(file_bytes)

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from this PDF."
        )

    risks, risk_score = detect_risks(text)
    clauses = detect_clauses(text)

    summary = create_summary(
        risks,
        clauses,
        text
    )

    document = Document(
        filename=file.filename,
        text=text,
        risk_score=risk_score,
        summary=summary
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

        # Split the PDF text into chunks
        chunks = split_into_chunks(text)

        # Generate embeddings and save each chunk
        for chunk_content in chunks:
            embedding = create_embedding(chunk_content)

            db.add(
                DocumentChunk(
                    document_id=document.id,
                    content=chunk_content,
                    embedding=embedding
                )
            )

        db.commit()

    except Exception as error:
        db.rollback()
        print("Document analysis error:", error)

        raise HTTPException(
            status_code=500,
            detail="Failed to save document chunks. Check the backend terminal."
        )

    return {
        "id": document.id,
        "filename": file.filename,
        "risk_score": risk_score,
        "summary": summary,
        "risks": risks,
        "clauses": clauses
    }

# --------------------------------------------------

# Ask AI
# --------------------------------------------------

class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    # Find the most recently uploaded document
    document = (
        db.query(Document)
        .order_by(Document.id.desc())
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=400,
            detail="Please analyze a document first."
        )

    # Create an embedding for the question
    question_embedding = create_embedding(request.question)

    # Retrieve the three closest chunks using vector similarity
    relevant_chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id
        )
        .order_by(
            DocumentChunk.embedding.cosine_distance(
                question_embedding
            )
        )
        .limit(3)
        .all()
    )

    if not relevant_chunks:
        raise HTTPException(
            status_code=400,
            detail="No document chunks found. Please upload the PDF again."
        )

    context = "\n\n".join(
        chunk.content for chunk in relevant_chunks
    )

    # Generate a grounded answer using the local Llama model
    try:
        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a contract analysis assistant. "
                        "Answer using only the supplied document context. "
                        "Be clear and concise. Do not invent contract terms. "
                        "If the answer is not available in the context, "
                        "say it is not clearly stated in the document."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Document context:\n{context}\n\n"
                        f"Question: {request.question}"
                    )
                }
            ]
        )

        return {
            "answer": response["message"]["content"].strip(),
            "document_id": document.id,
            "filename": document.filename
        }

    except Exception as error:
        print("Ollama error:", error)
        raise HTTPException(
            status_code=500,
            detail="Could not generate an answer. Check the backend terminal and confirm Ollama is running."
        )

    # ----------------------------------------------
    # Step 2: Build context
    # ----------------------------------------------

    context = "\n\n".join(
        relevant_chunks
    )

    # ----------------------------------------------
    # Step 3: Send context to local Ollama
    # ----------------------------------------------

    prompt = f"""
You are an AI contract analysis assistant.

Answer the user's question using ONLY the document context provided below.

Do not invent information.

If the answer is not clearly available in the context, say:

"The answer is not clearly stated in the uploaded document."

Give a clear and concise answer.

DOCUMENT CONTEXT:

{context}

USER QUESTION:

{request.question}

ANSWER:
"""

    payload = json.dumps({

        "model": "llama3.2:3b",

        "prompt": prompt,

        "stream": False

    }).encode("utf-8")

    try:

        req = urllib.request.Request(

            "http://localhost:11434/api/generate",

            data=payload,

            headers={
                "Content-Type":
                "application/json"
            },

            method="POST"
        )

        with urllib.request.urlopen(req) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        return {
            "answer":
            result["response"].strip()
        }

    except Exception as error:

        print(
            "Ollama error:",
            error
        )

        raise HTTPException(

            status_code=500,

            detail=
            "Could not connect to the local Ollama model."
        )