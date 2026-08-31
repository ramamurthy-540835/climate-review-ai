"""HTTP API for the IPCC Climate AI web client."""

import base64
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from services.comment_service import suggest_comment
from services.document_service import (
    get_document_text,
    get_documents,
    get_page_context,
    get_pdf_base64,
)
from services.improvement_service import improve_document
from services.llm_service import ask_question_with_sources
from services.review_service import review_document
from services.summary_service import summarize_document

app = FastAPI(title="IPCC Climate AI API", version="1.0.0")
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials="*" not in allowed_origins, allow_methods=["*"], allow_headers=["*"])

class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)

class DocumentRequest(BaseModel):
    document_name: str = Field(min_length=1, max_length=500)

class ReviewSuggestionRequest(BaseModel):
    document_name: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=100)
    page: int = Field(ge=1)
    from_line: int = Field(ge=0)
    to_line: int = Field(ge=0)
    selected_text: str = Field(min_length=1, max_length=12000)
    reviewer_note: str = Field(default="", max_length=4000)

def document_or_404(document_name: str) -> None:
    if not any(doc["real"] == document_name for doc in get_documents()):
        raise HTTPException(status_code=404, detail="Document not found")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/documents")
def documents():
    return {"documents": get_documents()}

@app.post("/api/ask")
def ask(request: QuestionRequest):
    try:
        answer, sources = ask_question_with_sources(request.question.strip())
        return {"answer": answer, "sources": sources}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to answer this question") from exc

@app.post("/api/document/{action}")
def document_action(action: Literal["summary", "review", "improvement"], request: DocumentRequest):
    try:
        document_or_404(request.document_name)
        text = get_document_text(request.document_name)
        handlers = {"summary": summarize_document, "review": review_document, "improvement": improve_document}
        return {"result": handlers[action](text)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process this document") from exc

@app.post("/api/review/suggest")
def review_suggestion(request: ReviewSuggestionRequest):
    """Generate a demo-only comment suggestion; never submit externally."""
    try:
        document_or_404(request.document_name)
        context = get_page_context(request.document_name, request.page)
        return suggest_comment(
            document_name=request.document_name,
            category=request.category,
            page=request.page,
            from_line=request.from_line,
            to_line=request.to_line,
            selected_text=request.selected_text.strip(),
            context=context,
            reviewer_note=request.reviewer_note.strip(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to draft a review suggestion") from exc

@app.get("/api/documents/{document_name:path}/pdf")
def pdf(document_name: str):
    try:
        document_or_404(document_name)
        pdf_bytes = base64.b64decode(get_pdf_base64(document_name))
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{os.path.basename(document_name)}"'})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to download this PDF") from exc
