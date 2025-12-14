"""
Mission Control API - Orchestrates autonomous lead generation missions
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from scrapers.scraping_service import scraping_service, log_agent_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mission", tags=["mission"])

class MissionRequest(BaseModel):
    prompt: str
    icp_profile_id: Optional[int] = None

async def run_mission(prompt: str, icp_profile_id: Optional[int]):
    """
    Orchestrate the mission using LangGraph Autonomous Agent
    """
    try:
        log_agent_event("Mission Control", f"Mission started: {prompt}", "info")
        
        # Execute LangGraph Workflow directly with the mission goal
        # The graph orchestrator handles the multi-agent steps (Search -> Scrape -> Classify -> Reason)
        from agents.graph import run_agent_mission
        await run_agent_mission(prompt)

        log_agent_event("Mission Control", "Mission completed", "success")

    except Exception as e:
        logger.error(f"Mission failed: {e}")
        log_agent_event("Mission Control", f"Mission failed: {str(e)}", "error")

@router.post("/launch")
async def launch_mission(
    request: MissionRequest,
    background_tasks: BackgroundTasks
):
    """
    Launch a new autonomous mission
    """
    background_tasks.add_task(run_mission, request.prompt, request.icp_profile_id)
    return {"status": "started", "message": "Mission launched"}
