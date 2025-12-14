"""
Simple FastAPI app for testing - no startup checks, simple search endpoint
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import init_db, engine

# Initialize database
init_db(engine)

app = FastAPI(
    title="Raptorflow Test API",
    description="Minimal API for testing",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for the search
class LeadFilter(BaseModel):
    score_min: int = 0
    score_max: int = 150
    status: Optional[str] = None
    score_bucket: Optional[str] = None
    decision_making_level: Optional[str] = None
    company_size_estimate: Optional[str] = None
    budget_authority: Optional[str] = None
    target_priority: Optional[str] = None
    urgency_level: Optional[str] = None
    role_type: Optional[str] = None
    company_name_contains: Optional[str] = None
    pain_tags_contains: Optional[str] = None
    economic_buyer_guess: Optional[str] = None
    executive_level_min: Optional[int] = None
    budget_potential_min: Optional[int] = None
    limit: int = 50
    offset: int = 0
    sort_by: str = "total_score"
    sort_desc: bool = True

class CompanySimple(BaseModel):
    id: int
    name: str
    website: Optional[str]
    sector: Optional[str]

class LeadResponse(BaseModel):
    id: int = 1
    company_id: int = 1
    contact_id: Optional[int] = None
    score_icp_fit: float = 85.0
    score_marketing_pain: float = 78.0
    score_data_quality: float = 92.0
    total_score: float = 85.0
    score_bucket: str = "warm"
    role_type: Optional[str] = "marketing_director"
    pain_tags: List[str] = ["budget_concerns", "growth_struggles"]
    status: str = "new"
    created_at: str = "2024-01-15T10:30:00Z"
    company: Optional[CompanySimple] = None

@app.get("/")
def root():
    return {"status": "ok", "service": "Raptorflow Test API"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Basic API running - no Ollama required"
    }

@app.post("/api/leads/search", response_model=List[LeadResponse])
def advanced_lead_search(filters: LeadFilter):
    """
    Mock advanced lead search - returns empty list since database is empty
    But this shows the endpoint is working
    """
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )
