"""
Scraping API endpoints
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import logging

from scrapers.scraping_service import scraping_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scrape", tags=["scraping"])


class JobBoardScrapeRequest(BaseModel):
    """Request for scraping job boards"""
    query: str
    location: Optional[str] = ""
    sources: Optional[List[str]] = None  # ['indeed', 'naukri', 'linkedin']
    num_pages: Optional[int] = 3


class CompanyScrapeRequest(BaseModel):
    """Request for scraping a company website"""
    url: HttpUrl
    company_name: Optional[str] = None
    deep_scan: Optional[bool] = False


class LeadDiscoveryRequest(BaseModel):
    """Request for discovering leads via search"""
    search_query: str
    num_results: Optional[int] = 20
    scrape_companies: Optional[bool] = False


class CareerPageScrapeRequest(BaseModel):
    """Request for scraping a career page"""
    url: HttpUrl
    company_name: str


class StartupScrapeRequest(BaseModel):
    """Request for scraping startup listings"""
    source: str = "ycombinator"
    query: Optional[str] = ""


class CustomUrlsRequest(BaseModel):
    """Request for scraping custom URLs"""
    urls: List[HttpUrl]


@router.post("/job-boards", summary="Scrape job boards for leads")
async def scrape_job_boards(
    request: JobBoardScrapeRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Scrape multiple job boards for job postings and create leads

    This endpoint launches background tasks to scrape job boards (Indeed, Naukri, LinkedIn).
    It returns immediately with a confirmation.

    **Parameters:**
    - **query**: Job search query (e.g., "marketing manager", "growth hacker")
    - **location**: Optional location filter
    - **sources**: List of sources to scrape ['indeed', 'naukri', 'linkedin'] (default: indeed, naukri)
    - **num_pages**: Number of pages to scrape per source (default: 3)

    **Returns:**
    - Status message indicating scrape has started
    """
    try:
        logger.info(f"Starting job board scrape background task: {request.query}")

        # Run scraping in background
        background_tasks.add_task(
            scraping_service.scrape_job_boards,
            query=request.query,
            location=request.location or "",
            sources=request.sources,
            num_pages=request.num_pages or 3
        )

        return {
            "status": "started",
            "message": f"Job board scrape for '{request.query}' started in background.",
            "details": {
                "sources": request.sources or ["indeed", "naukri"],
                "pages": request.num_pages or 3
            }
        }

    except Exception as e:
        logger.error(f"Error queuing job board scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/company-website", summary="Scrape company website")
async def scrape_company_website(
    request: CompanyScrapeRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Scrape a company website for contact info and hiring signals

    Launches a background task to crawl the company website.

    **Parameters:**
    - **url**: Company website URL
    - **company_name**: Optional company name
    - **deep_scan**: If true, also crawls career and contact pages

    **Returns:**
    - Status message
    """
    try:
        logger.info(f"Starting company website scrape background task: {request.url}")

        background_tasks.add_task(
            scraping_service.scrape_company_website,
            url=str(request.url),
            company_name=request.company_name,
            deep_scan=request.deep_scan or False
        )

        return {
            "status": "started",
            "message": f"Scrape for {request.url} started in background."
        }

    except Exception as e:
        logger.error(f"Error queuing company scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover-leads", summary="Discover new leads via search")
async def discover_leads(
    request: LeadDiscoveryRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Discover new potential leads via search engines

    Launches background task to search and optionally scrape companies.

    **Parameters:**
    - **search_query**: Search query
    - **num_results**: Number of search results to fetch
    - **scrape_companies**: If true, also scrapes each discovered company website

    **Returns:**
    - Status message
    """
    try:
        logger.info(f"Starting lead discovery background task: {request.search_query}")

        background_tasks.add_task(
            scraping_service.discover_leads,
            search_query=request.search_query,
            num_results=request.num_results or 20,
            scrape_companies=request.scrape_companies or False
        )

        return {
            "status": "started",
            "message": f"Lead discovery for '{request.search_query}' started in background."
        }

    except Exception as e:
        logger.error(f"Error queuing lead discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/career-page", summary="Scrape a career/jobs page")
async def scrape_career_page(
    request: CareerPageScrapeRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Scrape a specific career/jobs page for job postings

    Launches background task.

    **Parameters:**
    - **url**: Career page URL
    - **company_name**: Company name

    **Returns:**
    - Status message
    """
    try:
        logger.info(f"Starting career page scrape background task: {request.url}")

        background_tasks.add_task(
            scraping_service.scrape_career_page,
            url=str(request.url),
            company_name=request.company_name
        )

        return {
            "status": "started",
            "message": f"Career page scrape for {request.company_name} started in background."
        }

    except Exception as e:
        logger.error(f"Error queuing career page scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/startup-listings", summary="Scrape startup directories")
async def scrape_startup_listings(
    request: StartupScrapeRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Scrape startup listings (e.g. YCombinator) for leads

    Launches background task.

    **Parameters:**
    - **source**: Source name
    - **query**: Search query

    **Returns:**
    - Status message
    """
    try:
        logger.info(f"Starting startup listings scrape background task: {request.source}")

        background_tasks.add_task(
            scraping_service.scrape_startup_listings,
            source=request.source,
            query=request.query
        )

        return {
            "status": "started",
            "message": f"Startup listing scrape ({request.source}) started in background."
        }

    except Exception as e:
        logger.error(f"Error queuing startup scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom-urls", summary="Scrape custom URL list")
async def scrape_custom_urls(
    request: CustomUrlsRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Scrape a provided list of URLs for leads

    Launches background task.

    **Parameters:**
    - **urls**: List of URLs to scrape

    **Returns:**
    - Status message
    """
    try:
        logger.info(f"Starting custom URLs scrape background task: {len(request.urls)} URLs")

        background_tasks.add_task(
            scraping_service.scrape_custom_urls,
            urls=[str(u) for u in request.urls]
        )

        return {
            "status": "started",
            "message": f"Scrape for {len(request.urls)} custom URLs started in background."
        }

    except Exception as e:
        logger.error(f"Error queuing custom URLs scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", summary="List available scraping sources")
async def list_scraping_sources() -> Dict[str, Any]:
    """
    List all available scraping sources and their capabilities

    Returns information about which job boards and sources can be scraped.
    """
    return {
        "job_boards": [
            {
                "name": "indeed",
                "description": "Indeed.com - Global job board",
                "regions": ["Global"],
                "rate_limit": "2 seconds between requests"
            },
            {
                "name": "naukri",
                "description": "Naukri.com - Indian job board",
                "regions": ["India"],
                "rate_limit": "2 seconds between requests"
            },
            {
                "name": "linkedin",
                "description": "LinkedIn Jobs - Professional network (limited, may be blocked)",
                "regions": ["Global"],
                "rate_limit": "3 seconds between requests",
                "notes": "LinkedIn actively blocks scrapers, use with caution"
            }
        ],
        "search_engines": [
            {
                "name": "duckduckgo",
                "description": "DuckDuckGo search for lead discovery",
                "rate_limit": "2 seconds between requests"
            }
        ],
        "company_scraping": {
            "description": "Scrape any company website for contact info and hiring signals",
            "features": [
                "Extract contact emails and phones",
                "Find career page URLs",
                "Detect hiring signals",
                "Extract social media links",
                "Identify technologies used",
                "Estimate company size"
            ]
        },
        "startup_listings": [
            {
                "name": "ycombinator",
                "description": "Y Combinator Companies Directory",
                "regions": ["Global"],
                "rate_limit": "2 seconds between requests"
            }
        ],
        "custom_sources": {
            "description": "Scrape custom lists of URLs (forums, blogs, directories)",
            "features": [
                "Extract company info",
                "Detect hiring signals",
                "Create leads"
            ]
        }
    }


@router.get("/health", summary="Check scraping service health")
async def scraping_health() -> Dict[str, str]:
    """
    Check if scraping service is ready

    Returns the status of the scraping service.
    """
    return {
        "status": "healthy",
        "message": "Scraping service is ready"
    }
