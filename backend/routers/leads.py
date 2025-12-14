"""Lead management - CRUD and scoring."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
from pathlib import Path
from fastapi.responses import FileResponse
from database import Lead, Company, Contact, Signal, Activity, OutreachLog, SessionLocal
from lead_upsert import upsert_lead as upsert_lead_helper
from export_service import generate_lead_pdf
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic schemas
class CompanySimple(BaseModel):
    id: int
    name: str
    website: Optional[str]
    sector: Optional[str]

    class Config:
        from_attributes = True

class ContactSimple(BaseModel):
    id: int
    name: Optional[str]
    role: Optional[str]
    email: Optional[str]
    phone_numbers: list

    class Config:
        from_attributes = True

class SignalSimple(BaseModel):
    id: int
    source_type: str
    source_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ActivitySimple(BaseModel):
    id: int
    type: str
    content: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class LeadResponse(BaseModel):
    id: int
    company_id: int
    contact_id: Optional[int]
    score_icp_fit: float
    score_marketing_pain: float
    score_data_quality: float
    total_score: float
    score_bucket: str
    role_type: Optional[str]
    pain_tags: list
    status: str
    created_at: datetime
    updated_at: datetime
    context_dossier: Optional[str]
    challenger_insight: Optional[str]
    reframe_suggestion: Optional[str]
    company: Optional[CompanySimple]
    contact: Optional[ContactSimple]
    signals: List[SignalSimple] = []
    activities: List[ActivitySimple] = []
    
    # Expanded fields
    situation: Optional[str] = None
    problem: Optional[str] = None
    implication: Optional[str] = None
    need_payoff: Optional[str] = None
    economic_buyer_guess: Optional[str] = None
    key_pain: Optional[str] = None

    class Config:
        from_attributes = True

class LeadFilter(BaseModel):
    # Basic filters
    score_min: int = 0
    score_max: int = 150  # Adjusted for new scoring system
    status: Optional[str] = None
    score_bucket: Optional[str] = None

    # Advanced executive-level filters
    decision_making_level: Optional[str] = None  # "founder_ceo", "c_level", "vp_director", "manager", "individual"
    company_size_estimate: Optional[str] = None   # "startup_1_10", "small_11_50", "medium_51_200", "large_200_plus", "enterprise_1000_plus"
    budget_authority: Optional[str] = None        # "high_yes", "medium_maybe", "low_no"
    target_priority: Optional[str] = None         # "strategic_gold", "high_value", "medium_potential", "low_pass"
    urgency_level: Optional[str] = None           # "immediate_crisis", "quarterly_priority", "future_plan", "nice_to_have"
    role_type: Optional[str] = None               # "marketing_leader", "founder_ceo", "cto_tech", etc.

    # Text search
    company_name_contains: Optional[str] = None
    pain_tags_contains: Optional[str] = None
    economic_buyer_guess: Optional[str] = None
    city_contains: Optional[str] = None

    # Date ranges
    created_after: Optional[str] = None  # ISO date string
    created_before: Optional[str] = None # ISO date string

    # Scoring thresholds
    executive_level_min: Optional[int] = None
    budget_potential_min: Optional[int] = None

    # Pagination
    limit: int = 50
    offset: int = 0
    sort_by: str = "total_score"  # "total_score", "executive_level", "budget_potential", "created_at", "company_name"
    sort_desc: bool = True

class LeadUpsertInput(BaseModel):
    company_name: str
    company_website: Optional[str] = None
    contact_name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None

class LeadUpsertResponse(BaseModel):
    status: str
    lead_id: int
    company_id: int
    contact_id: Optional[int]

class OutreachLogCreate(BaseModel):
    outreach_type: str
    message_sent: Optional[str] = None

class OutreachLogResponse(BaseModel):
    id: int
    lead_id: int
    outreach_type: str
    message_sent: Optional[str]
    sent_at: datetime
    response_received: bool
    response_text: Optional[str]

    class Config:
        from_attributes = True

@router.post("/search", response_model=List[LeadResponse])
def advanced_lead_search(
    filters: LeadFilter,
    db: Session = Depends(get_db),
):
    """
    Advanced lead search with comprehensive filtering capabilities.
    Focuses on high-value executive prospects.
    """
    query = db.query(Lead).join(Company, Lead.company_id == Company.id)

    # Basic scoring filters
    if filters.score_min > 0:
        query = query.filter(Lead.total_score >= filters.score_min)
    if filters.score_max < 150:
        query = query.filter(Lead.total_score <= filters.score_max)

    # Status and bucket filters
    if filters.status:
        query = query.filter(Lead.status == filters.status)
    if filters.score_bucket:
        query = query.filter(Lead.score_bucket == filters.score_bucket)

    # High-value executive filters (stored in metadata or extended fields)
    # Note: These would be stored during classification in a metadata JSON field
    # For now, we'll use existing role_type and other approximate matches

    if filters.decision_making_level:
        # Map high-level roles to executive levels
        if filters.decision_making_level == "founder_ceo":
            query = query.filter(Lead.economic_buyer_guess.in_(["founder", "ceo"]))
        elif filters.decision_making_level == "c_level":
            query = query.filter(Lead.economic_buyer_guess.in_(["cmo", "cto", "cfo"]))
        elif filters.decision_making_level == "vp_director":
            query = query.filter(Lead.economic_buyer_guess.in_(["vp", "director"]))

    # Budget authority filtering
    if filters.budget_authority == "high_yes":
        # High executive levels with marketing pain indicate budget authority
        query = query.filter(Lead.score_executive_level >= 20)
        query = query.filter(Lead.score_budget_potential >= 15)

    # Target priority filtering
    if filters.target_priority == "strategic_gold":
        # Highest scoring leads with executive level
        query = query.filter(Lead.total_score >= 100)
        query = query.filter(Lead.score_executive_level >= 20)

    # Company size filtering (NEW - Missing implementation)
    if filters.company_size_estimate:
        # We need to map company size to actual company data
        # Since we don't have company size in lead table yet, filter by score which correlates
        if filters.company_size_estimate == "no_micro":
            # Reject companies <5 employees - correlates with very low budget potential
            query = query.filter(Lead.score_budget_potential >= 10)
        elif filters.company_size_estimate == "5_plus":
            query = query.filter(Lead.score_budget_potential >= 8)
        elif filters.company_size_estimate == "10_plus":
            query = query.filter(Lead.score_budget_potential >= 12)
        elif filters.company_size_estimate == "20_plus":
            query = query.filter(Lead.score_budget_potential >= 15)
        elif filters.company_size_estimate == "50_plus":
            query = query.filter(Lead.score_executive_level >= 20)
        elif filters.company_size_estimate == "enterprise":
            query = query.filter(Lead.score_executive_level >= 25)
            query = query.filter(Lead.score_budget_potential >= 18)

    # Role type filtering
    if filters.role_type:
        if filters.role_type == "marketing_leader":
            query = query.filter(Lead.economic_buyer_guess.in_(["cmo", "vp", "director"]))
            query = query.filter(Lead.pain_tags.contains(["leadership"]))
        elif filters.role_type == "founder_ceo":
            query = query.filter(Lead.economic_buyer_guess.in_(["founder", "ceo"]))
        elif filters.role_type == "cto_tech":
            query = query.filter(Lead.economic_buyer_guess.in_(["cto"]))

    # Text search filters
    if filters.company_name_contains:
        query = query.filter(Company.name.ilike(f"%{filters.company_name_contains}%"))

    if filters.pain_tags_contains:
        query = query.filter(Lead.pain_tags.contains([filters.pain_tags_contains]))

    if filters.economic_buyer_guess:
        query = query.filter(Lead.economic_buyer_guess == filters.economic_buyer_guess)

    if filters.city_contains:
        query = query.filter(Company.city.ilike(f"%{filters.city_contains}%"))

    # Date range filters
    if filters.created_after:
        try:
            after_date = datetime.fromisoformat(filters.created_after.replace('Z', '+00:00'))
            query = query.filter(Lead.created_at >= after_date)
        except:
            pass

    if filters.created_before:
        try:
            before_date = datetime.fromisoformat(filters.created_before.replace('Z', '+00:00'))
            query = query.filter(Lead.created_at <= before_date)
        except:
            pass

    # Additional scoring thresholds
    if filters.executive_level_min:
        query = query.filter(Lead.score_executive_level >= filters.executive_level_min)

    if filters.budget_potential_min:
        query = query.filter(Lead.score_budget_potential >= filters.budget_potential_min)

    # Sorting
    sort_column = getattr(Lead, filters.sort_by, Lead.total_score)
    if filters.sort_desc:
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    total_count = query.count()  # Get total before pagination
    leads = query.offset(filters.offset).limit(filters.limit).all()

    # Add metadata about the search
    result = []
    for lead in leads:
        lead_dict = LeadResponse.from_orm(lead).__dict__
        lead_dict['_search_metadata'] = {
            'total_matches': total_count,
            'applied_filters': {
                'executive_level': lead.score_executive_level,
                'budget_potential': lead.score_budget_potential,
                'priority_match': lead.score_executive_level >= 20 and lead.score_budget_potential >= 15
            }
        }
        result.append(lead_dict)

    return result

@router.get("/", response_model=List[LeadResponse])
def list_leads(
    score_min: int = 0,
    score_max: int = 150,
    status: Optional[str] = None,
    score_bucket: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List leads with basic filtering (backward compatibility)."""
    query = db.query(Lead)

    # Apply filters
    if score_min:
        query = query.filter(Lead.total_score >= score_min)
    if score_max < 150:
        query = query.filter(Lead.total_score <= score_max)
    if status:
        query = query.filter(Lead.status == status)
    if score_bucket:
        query = query.filter(Lead.score_bucket == score_bucket)

    # Sort by score descending (hottest first)
    leads = query.order_by(Lead.total_score.desc()).offset(offset).limit(limit).all()
    return leads

@router.post("/upsert", response_model=LeadUpsertResponse)
def upsert_lead(
    payload: LeadUpsertInput,
    db: Session = Depends(get_db),
):
    try:
        result = upsert_lead_helper(
            db,
            company_name=payload.company_name,
            company_website=payload.company_website,
            contact_name=payload.contact_name,
            role=payload.role,
            email=payload.email,
            phone=payload.phone,
            linkedin_url=payload.linkedin_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    lead = result.get("lead")
    company = result.get("company")
    contact = result.get("contact")

    if result.get("status") == "incomplete" or lead is None:
        raise HTTPException(
            status_code=400,
            detail="Incomplete lead. Requires contact name + valid email + valid phone + circumstances.",
        )
    db.commit()

    return LeadUpsertResponse(
        status=result.get("status", "created"),
        lead_id=lead.id,
        company_id=company.id,
        contact_id=contact.id if contact else None,
    )

@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.get("/{lead_id}/outreach", response_model=List[OutreachLogResponse])
def list_outreach_logs(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return (
        db.query(OutreachLog)
        .filter(OutreachLog.lead_id == lead_id)
        .order_by(OutreachLog.sent_at.desc())
        .all()
    )

@router.post("/{lead_id}/outreach", response_model=OutreachLogResponse)
def create_outreach_log(
    lead_id: int,
    payload: OutreachLogCreate,
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    log = OutreachLog(
        lead_id=lead_id,
        outreach_type=payload.outreach_type,
        message_sent=payload.message_sent,
        sent_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

@router.patch("/{lead_id}/status")
def update_lead_status(lead_id: int, status: str, db: Session = Depends(get_db)):
    """Update lead status and log activity."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    valid_statuses = ["new", "contacted", "qualified", "pitched", "trial", "won", "lost", "parked"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    old_status = lead.status
    lead.status = status
    lead.updated_at = datetime.utcnow()

    # Log activity
    activity = Activity(
        lead_id=lead.id,
        type="status_change",
        content=f"Status changed from {old_status} to {status}",
        timestamp=datetime.utcnow()
    )
    db.add(activity)
    
    db.commit()
    return {"status": "ok", "lead_id": lead_id, "new_status": status}

@router.patch("/{lead_id}/notes")
def update_lead_notes(lead_id: int, notes: str, db: Session = Depends(get_db)):
    """Update lead notes and log activity."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # We append to the existing notes field (or overwrite if that's the desired behavior, 
    # but usually notes are a history. However, the UI sends a single string.)
    # If the UI sends the *new* note content, we should probably append it or store it in Activity.
    # The current requirement says "Provide a textarea... to add a note... On save, send it... and then display it".
    # So we'll treat the payload as a NEW note to be added to Activity, 
    # and maybe update the `notes` field to be the "latest note" or just append.
    
    # Let's do both: Update the main notes field (append) AND create an activity.
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_note_entry = f"[{timestamp}] {notes}"
    
    if lead.notes:
        lead.notes = lead.notes + "\n\n" + new_note_entry
    else:
        lead.notes = new_note_entry

    lead.updated_at = datetime.utcnow()
    
    # Log activity
    activity = Activity(
        lead_id=lead.id,
        type="note",
        content=notes,
        timestamp=datetime.utcnow()
    )
    db.add(activity)

    db.commit()
    return {"status": "ok"}

@router.get("/score-distribution/bucket-counts")
def get_bucket_counts(db: Session = Depends(get_db)):
    """Get count of leads by score bucket."""
    from sqlalchemy import func

    counts = db.query(
        Lead.score_bucket,
        func.count(Lead.id).label("count")
    ).group_by(Lead.score_bucket).all()

    return {
        "red_hot": next((c[1] for c in counts if c[0] == "red_hot"), 0),
        "warm": next((c[1] for c in counts if c[0] == "warm"), 0),
        "nurture": next((c[1] for c in counts if c[0] == "nurture"), 0),
        "parked": next((c[1] for c in counts if c[0] == "parked"), 0),
    }

@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """Delete a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()
    return {"message": "Lead deleted"}


@router.get("/{lead_id}/export/pdf")
def export_lead_pdf(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    assets_dir = Path(__file__).resolve().parents[1] / "assets"
    result = generate_lead_pdf(lead=lead, assets_dir=assets_dir)

    return FileResponse(
        path=str(result.file_path),
        media_type="application/pdf",
        filename=result.file_path.name,
    )

@router.get("/export/csv")
def export_leads_csv(db: Session = Depends(get_db)):
    """Export all leads to CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    def iter_csv():
        f = io.StringIO()
        writer = csv.writer(f)
        
        # Headers
        headers = [
            "ID", "Company", "Website", "Score", "Bucket", "Status", "Role Type", 
            "Contact Name", "Contact Email", "Contact Phone",
            "Key Pain", "Decision Level", "Budget Potential"
        ]
        writer.writerow(headers)
        f.seek(0)
        yield f.read()
        f.truncate(0)
        f.seek(0)

        # Data
        leads = db.query(Lead).join(Company).order_by(Lead.total_score.desc()).all()
        
        for lead in leads:
            row = [
                lead.id,
                lead.company.name,
                lead.company.website or "",
                lead.total_score,
                lead.score_bucket,
                lead.status,
                lead.role_type or "",
                lead.contact.name if lead.contact else "",
                lead.contact.email if lead.contact else "",
                ", ".join(lead.contact.phone_numbers) if lead.contact and lead.contact.phone_numbers else "",
                lead.key_pain or "",
                lead.score_executive_level,
                lead.score_budget_potential
            ]
            writer.writerow(row)
            f.seek(0)
            yield f.read()
            f.truncate(0)
            f.seek(0)

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )
