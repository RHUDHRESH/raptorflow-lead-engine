"""API endpoints for managing scrape schedules."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from database import SessionLocal, ScrapeSchedule
from scheduled_tasks import refresh_scheduler, execute_scrape_job

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ScheduleCreate(BaseModel):
    name: str
    schedule_type: str # "cron", "interval"
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    job_type: str # "job_boards", "startup_listings", "custom_urls"
    job_params: Dict[str, Any] = {}
    is_active: bool = True

class ScheduleResponse(ScheduleCreate):
    id: int
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ScheduleResponse])
def list_schedules(db: Session = Depends(get_db)):
    """List all scrape schedules."""
    return db.query(ScrapeSchedule).all()

@router.post("/", response_model=ScheduleResponse)
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    """Create a new scrape schedule."""
    db_schedule = ScrapeSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    refresh_scheduler()
    return db_schedule

@router.patch("/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int, active: bool, db: Session = Depends(get_db)):
    """Enable or disable a schedule."""
    schedule = db.query(ScrapeSchedule).filter(ScrapeSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.is_active = active
    db.commit()
    refresh_scheduler()
    return {"status": "updated", "is_active": active}

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule."""
    schedule = db.query(ScrapeSchedule).filter(ScrapeSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(schedule)
    db.commit()
    refresh_scheduler()
    return {"message": "Schedule deleted"}

@router.post("/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger a schedule to run immediately."""
    schedule = db.query(ScrapeSchedule).filter(ScrapeSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Run in background
    background_tasks.add_task(execute_scrape_job, schedule_id)
    return {"message": f"Job {schedule.name} triggered"}
