import os
import re
from io import BytesIO

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import InferenceClient
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Document, DocumentChunk


app = FastAPI(
    title="AI Document Intelligence API",
    version="1.0.0",
)

# Add your deployed Vercel URL to this list when it is available.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://ai-document-intelligence-flame.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


RISK_RULES = [
    {
        "name": "Non-Compete Clause",
        "keywords": ["non-compete", "non compete", "noncompetition"],
        "level": "High",
        "points": 25,
        "explanation": "This clause may restrict the party from working with competitors.",
    },
    {
        "name": "Termination Clause",
        "keywords": ["termination", "terminate this agreement", "termination of agreement"],
        "level": "Medium",
        "points": 15,
        "explanation": "Review termination conditions, notice periods and associated penalties.",
    },
    {
        "name": "Liability Clause",
        "keywords": ["liability", "liable", "limitation of liability"],
        "level": "High",
        "points": 20,
        "explanation": "This clause may define significant financial or legal responsibility.",
    },
    {
        "name": "Indemnity Clause",
        "keywords": ["indemnify", "indemnification", "indemnity"],
        "level": "High",
        "points": 20,
        "explanation": "Indemnity obligations can create financial and legal exposure.",
    },
    {
        "name": "Confidentiality Clause",
        "keywords": ["confidentiality", "confidential information", "non-disclosure"],
        "level": "Medium",
        "points": 10,
        "explanation": "Check what information is confidential and how long the obligation lasts.",
    },
    {
        "name": "Payment Clause",
        "keywords": ["payment", "invoice", "fees", "compensation"],
        "level": "Low",
        "points": 5,
        "explanation": "Review payment terms, deadlines and penalties.",
    },
]


def extract_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def split_into_chunks(text: str) -> list[str]:
    # Moderate-sized chunks make keyword retrieval more useful than tiny fragments.
    words = text.split()
    chunk_size = 180
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size]).strip()
        if len(chunk) > 20:
            chunks.append(chunk)
    return chunks[:100]


def detect_risks(text: str):
    lower_text = text.lower()
    risks = []
    score = 0

    for rule in RISK_RULES:
        if any(keyword in lower_text for keyword in rule["keywords"]):
            risks.append({
                "clause": rule["name"],
                "level": rule["level"],
                "explanation": rule["explanation"],
            })
            score += rule["points"]

    return risks, min(score, 100)


def detect_clauses(text: str) -> list[str]:
    lower_text = text.lower()
    clause_keywords = {
        "Termination": ["termination", "terminate"],
        "Confidentiality": ["confidentiality", "confidential information"],
        "Non-Compete": ["non-compete", "non compete"],
        "Liability": ["liability", "liable"],
        "Indemnity": ["indemnify", "indemnification", "indemnity"],
        "Payment": ["payment", "fees", "compensation"],
        "Intellectual Property": ["intellectual property", "copyright", "ownership"],
    }
    return [
        name
        for name, keywords in clause_keywords.items()
        if any(keyword in lower_text for keyword in keywords)
    ]


def create_summary(risks, clauses, document_text: str) -> str:
    if not document_text:
        return "No readable text was extracted from this document."
    if not risks:
        return (
            f"The document contains {len(clauses)} recognized clause categories. "
            "No major predefined risk patterns were detected."
        )
    names = ", ".join(risk["clause"] for risk in risks)
    return (
        f"The document contains {len(clauses)} recognized clause categories. "
        f"Potential risk areas detected: {names}. Review these clauses carefully."
    )


def select_relevant_chunks(chunks: list[str], question: str, limit: int = 3) -> list[str]:
    """Simple keyword-based retrieval; it avoids a separate embeddings API."""
    stop_words = {
        "what", "when", "where", "which", "who", "whom", "why", "how",
        "does", "did", "the", "and", "for", "with", "from", "this", "that",
        "are", "was", "were", "can", "could", "would", "should", "about",
        "tell", "please", "document", "contract",
    }
    terms = {
        term for term in re.findall(r"[a-zA-Z0-9]+", question.lower())
        if len(term) > 2 and term not in stop_words
    }

    if not terms:
        return chunks[:limit]

    ranked = []
    for index, chunk in enumerate(chunks):
        lower_chunk = chunk.lower()
        score = sum(lower_chunk.count(term) for term in terms)
        if score > 0:
            ranked.append((score, index, chunk))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return chunks[:limit]
    return [item[2] for item in ranked[:limit]]


def generate_answer(context: str, question: str) -> str:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not configured in the service environment.")

    client = InferenceClient(api_key=token)
    response = client.chat_completion(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a contract analysis assistant. Answer using only the supplied "
                    "document context. Be clear and concise. Do not invent contract terms. "
                    "If the answer is not available in the context, say it is not clearly "
                    "stated in the document. This is informational assistance, not legal advice."
                ),
            },
            {
                "role": "user",
                "content": f"Document context:\n{context}\n\nQuestion: {question}",
            },
        ],
        max_tokens=400,
        temperature=0.2,
    )
    answer = response.choices[0].message.content
    return (answer or "").strip()


@app.get("/")
def root():
    return {"message": "AI Document Intelligence API is running"}


@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        file_bytes = await file.read()
        document_text = extract_text(file_bytes)
    except Exception as error:
        print("PDF extraction error:", error)
        raise HTTPException(status_code=400, detail="Could not read this PDF file.")

    if not document_text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from this PDF. Scanned PDFs may require OCR.",
        )

    risks, risk_score = detect_risks(document_text)
    clauses = detect_clauses(document_text)
    summary = create_summary(risks, clauses, document_text)

    document = Document(
        filename=file.filename,
        text=document_text,
        risk_score=risk_score,
        summary=summary,
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

        chunks = split_into_chunks(document_text)
        for chunk_content in chunks:
            # The existing database model requires a 384-dimensional vector.
            # Zero vectors preserve schema compatibility; retrieval below uses keywords.
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    content=chunk_content,
                    embedding=[0.0] * 384,
                )
            )
        db.commit()
    except Exception as error:
        db.rollback()
        print("Document analysis/database error:", error)
        raise HTTPException(
            status_code=500,
            detail="Failed to save document. Check the backend logs.",
        )

    return {
        "id": document.id,
        "filename": file.filename,
        "risk_score": risk_score,
        "summary": summary,
        "risks": risks,
        "clauses": clauses,
    }


class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db),
):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    document = db.query(Document).order_by(Document.id.desc()).first()
    if not document:
        raise HTTPException(status_code=400, detail="Please analyze a document first.")

    stored_chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .all()
    )
    if not stored_chunks:
        raise HTTPException(
            status_code=400,
            detail="No document chunks found. Please upload the PDF again.",
        )

    selected_chunks = select_relevant_chunks(
        [chunk.content for chunk in stored_chunks],
        question,
    )
    context = "\n\n".join(selected_chunks)

    try:
        answer = generate_answer(context, question)
        return {
            "answer": answer,
            "document_id": document.id,
            "filename": document.filename,
        }
    except Exception as error:
        print("Hugging Face error:", error)
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not generate an answer. Check HF_TOKEN, Hugging Face model "
                "availability, inference permissions, and backend logs."
            ),
        )
