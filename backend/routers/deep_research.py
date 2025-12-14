"""
Deep Research APIs - Social media, news intelligence, tech stack analysis
Provide sales teams with unfair competitive advantage through proprietary research
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import asyncio
from database import SessionLocal, Lead, Company
from scrapers.enhanced_scrapers import SocialScraper, NewsScraper, TechStackScraper

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DeepResearchRequest(BaseModel):
    lead_id: int
    include_social: bool = True
    include_news: bool = True
    include_tech_stack: bool = True

class ResearchResult(BaseModel):
    lead_id: int
    company_name: str
    research_completed_at: str
    social_profiles: Optional[Dict[str, Any]] = None
    news_mentions: Optional[List[Dict[str, Any]]] = None
    tech_stack: Optional[Dict[str, Any]] = None
    status: str = "completed"

@router.post("/lead/{lead_id}", response_model=ResearchResult)
async def research_lead(
    lead_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Perform deep research on a lead - social profiles, news, tech stack.
    This provides unique intelligence no other salesperson has.
    """
    # Get lead and company info
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    company = lead.company
    if not company:
        raise HTTPException(status_code=404, detail="Company not found for lead")

    # Initialize scrapers
    social_scraper = SocialScraper()
    news_scraper = NewsScraper()
    tech_scraper = TechStackScraper()

    result = {
        "lead_id": lead_id,
        "company_name": company.name,
        "research_completed_at": datetime.now().isoformat(),
        "social_profiles": {},
        "news_mentions": [],
        "tech_stack": {},
        "status": "completed"
    }

    try:
        # Social media research
        if company.website:
            result["social_profiles"] = await _research_social_profiles(
                social_scraper, company.name, company.website
            )

        # News research
        result["news_mentions"] = news_scraper.search_company_news(company.name, days_back=90)

        # Tech stack analysis
        if company.website:
            result["tech_stack"] = tech_scraper.detect_tech_stack(company.website)

        # Update lead with research data
        lead.social_profiles = result["social_profiles"]
        lead.news_mentions = result["news_mentions"]
        lead.tech_stack = result["tech_stack"]
        lead.updated_at = datetime.now()
        db.commit()

    except Exception as e:
        result["status"] = f"error: {str(e)}"

    return result

@router.get("/lead/{lead_id}", response_model=ResearchResult)
def get_research_results(lead_id: int, db: Session = Depends(get_db)):
    """Get existing research results for a lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    company = lead.company
    return {
        "lead_id": lead_id,
        "company_name": company.name if company else "Unknown",
        "research_completed_at": lead.updated_at.isoformat() if lead.updated_at else None,
        "social_profiles": lead.social_profiles,
        "news_mentions": lead.news_mentions,
        "tech_stack": lead.tech_stack,
        "status": "completed"
    }

async def _research_social_profiles(
    scraper: SocialScraper,
    company_name: str,
    website: str
) -> Dict[str, Any]:
    """Research company's social media presence"""
    social_data = {}

    try:
        # Try LinkedIn company page
        linkedin_url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}"
        linkedin_data = scraper.scrape_linkedin_profile(linkedin_url)
        if linkedin_data and linkedin_data.get('name'):
            social_data['linkedin'] = linkedin_data

        # Try Twitter
        twitter_handle = f"{company_name.replace(' ', '').lower()}"
        twitter_data = scraper.scrape_twitter_profile(twitter_handle)
        if twitter_data and twitter_data.get('name'):
            social_data['twitter'] = twitter_data

        # Try common variations
        if not social_data.get('twitter'):
            for variation in ['co', 'hq', 'team']:
                handle = f"{company_name.replace(' ', '').lower()}{variation}"
                twitter_data = scraper.scrape_twitter_profile(handle)
                if twitter_data and twitter_data.get('name'):
                    social_data['twitter'] = twitter_data
                    break

    except Exception as e:
        social_data['error'] = str(e)

    return social_data

@router.post("/batch-research")
async def batch_deep_research(
    lead_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Perform deep research on multiple leads in background
    """
    results = []

    for lead_id in lead_ids:
        try:
            # Queue background research
            background_tasks.add_task(research_lead_bg, lead_id, db)
            results.append({"lead_id": lead_id, "status": "queued"})
        except Exception as e:
            results.append({"lead_id": lead_id, "status": "error", "error": str(e)})

    return {"results": results, "message": f"Queued research for {len(lead_ids)} leads"}

async def research_lead_bg(lead_id: int, db: Session):
    """Background task for lead research"""
    try:
        # Create new session for background task
        bg_db = SessionLocal()

        lead = bg_db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return

        company = lead.company
        if not company or not company.website:
            return

        # Initialize scrapers
        social_scraper = SocialScraper()
        news_scraper = NewsScraper()
        tech_scraper = TechStackScraper()

        # Research
        social_data = await _research_social_profiles(
            social_scraper, company.name, company.website
        )
        news_data = news_scraper.search_company_news(company.name, days_back=90)
        tech_data = tech_scraper.detect_tech_stack(company.website)

        # Update lead
        lead.social_profiles = social_data
        lead.news_mentions = news_data
        lead.tech_stack = tech_data
        lead.updated_at = datetime.now()
        bg_db.commit()

    finally:
        bg_db.close()

@router.get("/company/{domain}/intelligence")
async def get_company_intelligence(domain: str):
    """
    Get comprehensive intelligence on a company domain
    """
    try:
        # Parse company name from domain
        company_name = domain.split('.')[0].replace('-', ' ').title()

        # Initialize scrapers
        news_scraper = NewsScraper()
        tech_scraper = TechStackScraper()
        social_scraper = SocialScraper()

        # Parallel research
        social_task = _research_social_profiles(social_scraper, company_name, f"https://{domain}")
        news_task = asyncio.to_thread(news_scraper.search_company_news, company_name, 90)
        tech_task = asyncio.to_thread(tech_scraper.detect_tech_stack, f"https://{domain}")

        social_data, news_data, tech_data = await asyncio.gather(
            social_task, news_task, tech_task
        )

        # Generate competitive intelligence insights
        insights = _generate_competitive_insights(social_data, news_data, tech_data)

        return {
            "company_name": company_name,
            "domain": domain,
            "intelligence": {
                "social_presence": social_data,
                "recent_news": news_data[:10],  # Top 10 news items
                "technology_stack": tech_data,
                "competitive_insights": insights
            },
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intelligence gathering failed: {str(e)}")

def _generate_competitive_insights(social_data: dict, news_data: list, tech_data: dict) -> Dict[str, Any]:
    """Generate strategic insights from research data"""
    insights = {
        "funding_signals": [],
        "growth_indicators": [],
        "competitive_risks": [],
        "market_positioning": "",
        "actionable_opportunities": []
    }

    # Analyze news for funding/product signals
    for news_item in news_data[:5]:
        title_lower = news_item.get('title', '').lower()
        if any(word in title_lower for word in ['funding', 'raises', 'investment', 'series']):
            insights['funding_signals'].append(news_item['title'])
        elif any(word in title_lower for word in ['growth', 'expands', 'acquires', 'partners']):
            insights['growth_indicators'].append(news_item['title'])

    # Analyze social media for engagement signals
    linkedin_data = social_data.get('linkedin', {})
    if linkedin_data.get('connections') == '500+':
        insights['market_positioning'] = "Established player with strong network"
    elif linkedin_data.get('posts'):
        insights['market_positioning'] = "Active thought leader in industry"

    # Tech stack insights
    if tech_data.get('platform') == 'shopify':
        insights['actionable_opportunities'].append("E-commerce focused - target conversion optimization")
    if tech_data.get('analytics') and 'google_analytics' not in tech_data['analytics']:
        insights['actionable_opportunities'].append("Analytics gap - data-driven marketing opportunity")

    if 'facebook_pixel' not in str(tech_data.get('analytics', [])):
        insights['competitive_risks'].append("Limited retargeting capability")

    return insights

@router.get("/market-intelligence/{industry}")
def get_market_intelligence(industry: str):
    """
    Get market-level intelligence for industry targeting
    """
    # This would aggregate data from multiple sources for industry trends
    # For now, return framework for the feature
    return {
        "industry": industry,
        "market_signals": [
            "Key hiring trends",
            "Common pain points",
            "Successful competitor strategies",
            "Emerging technologies"
        ],
        "recommendations": [
            "ICP refinement opportunities",
            "Messaging angles to test",
            "Objection handling based on market data"
        ],
        "note": "Market intelligence aggregation coming in next update"
    }
