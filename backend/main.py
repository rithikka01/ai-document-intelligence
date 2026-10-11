

import os

import re

import requests

from io import BytesIO

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

from sqlalchemy.orm import Session

from database import Base, engine, get_db

from models import Document, DocumentChunk

app = FastAPI(

    title="AI Document Intelligence API",

    version="1.0.0",

)

# --------------------------------------------------

# CORS

# --------------------------------------------------

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

# Create database tables

Base.metadata.create_all(bind=engine)

# --------------------------------------------------

# Risk detection rules

# --------------------------------------------------

RISK_RULES = [

    {

        "name": "Non-Compete Clause",

        "keywords": ["non-compete", "non compete", "noncompetition"],

        "level": "High",

        "points": 25,

        "explanation": (

            "This clause may restrict the party from working with competitors."

        ),

    },

    {

        "name": "Termination Clause",

        "keywords": [

            "termination",

            "terminate this agreement",

            "termination of agreement",

        ],

        "level": "Medium",

        "points": 15,

        "explanation": (

            "Review termination conditions, notice periods and associated penalties."

        ),

    },

    {

        "name": "Liability Clause",

        "keywords": ["liability", "liable", "limitation of liability"],

        "level": "High",

        "points": 20,

        "explanation": (

            "This clause may define significant financial or legal responsibility."

        ),

    },

    {

        "name": "Indemnity Clause",

        "keywords": ["indemnify", "indemnification", "indemnity"],

        "level": "High",

        "points": 20,

        "explanation": (

            "Indemnity obligations can create financial and legal exposure."

        ),

    },

    {

        "name": "Confidentiality Clause",

        "keywords": [

            "confidentiality",

            "confidential information",

            "non-disclosure",

        ],

        "level": "Medium",

        "points": 10,

        "explanation": (

            "Check what information is confidential and how long the obligation lasts."

        ),

    },

    {

        "name": "Payment Clause",

        "keywords": ["payment", "invoice", "fees", "compensation"],

        "level": "Low",

        "points": 5,

        "explanation": (

            "Review payment terms, deadlines and penalties."

        ),

    },

]

# --------------------------------------------------

# PDF extraction and chunking

# --------------------------------------------------

def extract_text(file_bytes: bytes) -> str:

    reader = PdfReader(BytesIO(file_bytes))

    return "\n".join(

        page.extract_text() or ""

        for page in reader.pages

    ).strip()

def split_into_chunks(document_text: str) -> list[str]:

    words = document_text.split()

    chunk_size = 180

    chunks = []

    for i in range(0, len(words), chunk_size):

        chunk = " ".join(words[i:i + chunk_size]).strip()

        if len(chunk) > 20:

            chunks.append(chunk)

    return chunks[:100]

# --------------------------------------------------

# Risk and clause analysis

# --------------------------------------------------

def detect_risks(document_text: str):

    lower_text = document_text.lower()

    risks = []

    score = 0

    for rule in RISK_RULES:

        if any(

            keyword in lower_text

            for keyword in rule["keywords"]

        ):

            risks.append({

                "clause": rule["name"],

                "level": rule["level"],

                "explanation": rule["explanation"],

            })

            score += rule["points"]

    return risks, min(score, 100)

def detect_clauses(document_text: str) -> list[str]:

    lower_text = document_text.lower()

    clause_keywords = {

        "Termination": ["termination", "terminate"],

        "Confidentiality": [

            "confidentiality",

            "confidential information",

        ],

        "Non-Compete": ["non-compete", "non compete"],

        "Liability": ["liability", "liable"],

        "Indemnity": [

            "indemnify",

            "indemnification",

            "indemnity",

        ],

        "Payment": ["payment", "fees", "compensation"],

        "Intellectual Property": [

            "intellectual property",

            "copyright",

            "ownership",

        ],

    }

    return [

        name

        for name, keywords in clause_keywords.items()

        if any(keyword in lower_text for keyword in keywords)

    ]

def create_summary(

    risks: list,

    clauses: list[str],

    document_text: str,

) -> str:

    if not document_text:

        return "No readable text was extracted from this document."

    if not risks:

        return (

            f"The document contains {len(clauses)} recognized clause categories. "

            "No major predefined risk patterns were detected. "

            "This does not guarantee that the document is risk-free."

        )

    names = ", ".join(

        risk["clause"]

        for risk in risks

    )

    return (

        f"The document contains {len(clauses)} recognized clause categories. "

        f"Potential risk areas detected: {names}. "

        "Review these clauses carefully."

    )

# --------------------------------------------------

def select_relevant_chunks(

    chunks: list[str],

    question: str,

    limit: int = 3,

) -> list[str]:

    import re

    stop_words = {

        "what", "when", "where", "which", "who", "whom",

        "why", "how", "does", "did", "the", "and", "for",

        "with", "from", "this", "that", "are", "was", "were",

        "can", "could", "would", "should", "about", "tell",

        "please", "document", "contract", "explain", "show",

        "me", "is", "it", "of", "in", "to", "on", "a", "an",

        "say", "says", "clause", "agreement",

    }

    terms = {

        term

        for term in re.findall(r"[a-zA-Z0-9]+", question.lower())

        if len(term) > 2 and term not in stop_words

    }

    if not chunks:

        return []

    if not terms:

        return chunks[:limit]

    ranked = []

    for index, chunk in enumerate(chunks):

        words = set(re.findall(r"[a-zA-Z0-9]+", chunk.lower()))

        # Match exact words, avoiding misleading partial matches.

        score = sum(1 for term in terms if term in words)

        # Give extra weight to chunks containing multiple question terms.

        if score > 0:

            ranked.append((score, index, chunk))

    ranked.sort(key=lambda item: (-item[0], item[1]))

    # If no keywords match, provide the first chunks as fallback context.

    if not ranked:

        return chunks[:limit]

    return [item[2] for item in ranked[:limit]]

# --------------------------------------------------

# Gemini AI answer generation

# --------------------------------------------------

def generate_answer(context: str, question: str) -> str:

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:

        raise RuntimeError(

            "GEMINI_API_KEY is missing from the backend environment variables."

        )

    response = requests.post(

        (

            "https://generativelanguage.googleapis.com/"

            "v1beta/models/gemini-2.5-flash-lite:generateContent"

        ),

        headers={"Content-Type": "application/json"},

        params={"key": api_key},

        json={

            "contents": [

                {

                    "parts": [

                        {

                            "text": (

                                "You are a contract analysis assistant. "

                                "Answer using only the supplied document context. "

                                "Be clear and concise. Do not invent contract terms. "

                                "If the answer is unavailable, say it is not "

                                "clearly stated in the document. "

                                "This is informational assistance, not legal advice."

                                f"\n\nDocument context:\n{context}"

                                f"\n\nQuestion: {question}"

                            )

                        }

                    ]

                }

            ],

            "generationConfig": {

                "maxOutputTokens": 400,

                "temperature": 0.2,

            },

        },

        timeout=60,

    )

    if not response.ok:

        print("Gemini API response:", response.status_code, response.text)

    response.raise_for_status()

    data = response.json()

    answer = (

        data["candidates"][0]["content"]["parts"][0]["text"]

    )

    if not answer or not answer.strip():

        raise RuntimeError("The AI returned an empty answer.")

    return answer.strip()

# --------------------------------------------------

# Health check

# --------------------------------------------------

@app.get("/")

def root():

    return {

        "message": "AI Document Intelligence API is running"

    }

# --------------------------------------------------

# Analyze PDF

# --------------------------------------------------

@app.post("/analyze")

async def analyze_document(

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

):

    if (

        not file.filename

        or not file.filename.lower().endswith(".pdf")

    ):

        raise HTTPException(

            status_code=400,

            detail="Only PDF files are supported.",

        )

    try:

        file_bytes = await file.read()

        document_text = extract_text(file_bytes)

    except Exception as error:

        print("PDF extraction error:", error)

        raise HTTPException(

            status_code=400,

            detail="Could not read this PDF file.",

        )

    if not document_text:

        raise HTTPException(

            status_code=400,

            detail=(

                "Could not extract text from this PDF. "

                "Scanned PDFs may require OCR."

            ),

        )

    risks, risk_score = detect_risks(document_text)

    clauses = detect_clauses(document_text)

    summary = create_summary(

        risks,

        clauses,

        document_text,

    )

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

            db.add(

                DocumentChunk(

                    document_id=document.id,

                    content=chunk_content,

                )

            )

        db.commit()

    except Exception as error:

        db.rollback()

        print(

            "Document analysis/database error:",

            error,

        )

        raise HTTPException(

            status_code=500,

            detail=(

                "Failed to save the document. "

                "Check the backend logs and database models."

            ),

        )

    return {

        "id": document.id,

        "filename": file.filename,

        "risk_score": risk_score,

        "summary": summary,

        "risks": risks,

        "clauses": clauses,

    }

# --------------------------------------------------

# Ask AI about the latest uploaded document

# --------------------------------------------------

class QuestionRequest(BaseModel):

    question: str

@app.post("/ask")

def ask_question(

    request: QuestionRequest,

    db: Session = Depends(get_db),

):

    question = request.question.strip()

    if not question:

        raise HTTPException(

            status_code=400,

            detail="Question cannot be empty.",

        )

    document = (

        db.query(Document)

        .order_by(Document.id.desc())

        .first()

    )

    if not document:

        raise HTTPException(

            status_code=400,

            detail="Please analyze a document first.",

        )

    stored_chunks = (

        db.query(DocumentChunk)

        .filter(DocumentChunk.document_id == document.id)

        .all()

    )

    relevant_chunks = select_relevant_chunks(

        [chunk.content for chunk in stored_chunks],

        question,

        limit=3,

    )

    if relevant_chunks:

        context = "\n\n".join(relevant_chunks)

    else:

        context = (document.text or "").strip()

    if not context:

        raise HTTPException(

            status_code=400,

            detail=(

                "No extracted document text is available. "

                "Please upload the PDF again."

            ),

        )

    # Limit the amount of text sent to Gemini.

    context = context[:12000]

    try:

        answer = generate_answer(

            context=context,

            question=question,

        )

        return {

            "answer": answer,

            "document_id": document.id,

            "filename": document.filename,

        }

    except requests.exceptions.HTTPError as error:

        status_code = (

            error.response.status_code

            if error.response is not None

            else "unknown"

        )

        print("Gemini API HTTP error:", status_code, str(error))

        raise HTTPException(

            status_code=502,

            detail=(

                "The Gemini API returned an error. "

                "Check the backend logs and GEMINI_API_KEY configuration."

            ),

        )

    except requests.exceptions.RequestException as error:

        print("Gemini API connection error:", str(error))

        raise HTTPException(

            status_code=502,

            detail="Could not connect to the Gemini API.",

        )

    except Exception as error:

        print("AI answer generation error:", str(error))

        raise HTTPException(

            status_code=502,

            detail=(

                "Could not generate an answer. "

                "Check the backend logs and GEMINI_API_KEY environment variable."

            ),

        )
