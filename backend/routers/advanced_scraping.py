"""Advanced scraping endpoints - depth crawler, social media, scheduled tasks."""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from database import SessionLocal
from depth_crawler import DepthLimitedCrawler, summarize_crawled_text
from social_media_scraper import (
    LinkedInPublicScraper,
    NitterScraper,
    filter_hiring_posts,
    social_post_to_signal_text
)
from job_board_apis import JobBoardAPIClient, job_to_signal_text
from scheduled_tasks import get_scheduled_jobs, trigger_job_now
from routers.classify import SignalInput, classify_signal as classify_signal_func

logger = logging.getLogger(__name__)
router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Depth-Limited Website Crawler
# ============================================================================

class CrawlWebsiteInput(BaseModel):
    """Input for website crawling."""
    url: str
    max_pages: int = 5
    max_depth: int = 2
    auto_classify: bool = True


@router.post("/crawl/website")
async def crawl_website(
    input_data: CrawlWebsiteInput,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Crawl a website with depth-limiting (default 5 pages).
    Extracts text from /about, /careers, /jobs, /blog pages.
    Summarizes text and optionally classifies as a lead signal.

    Args:
        url: Starting URL to crawl
        max_pages: Maximum number of pages to crawl (default: 5)
        max_depth: Maximum depth from start URL (default: 2)
        auto_classify: If True, classify the crawled content as a signal
    """
    try:
        crawler = DepthLimitedCrawler(
            max_pages=input_data.max_pages,
            max_depth=input_data.max_depth,
        )

        # Crawl the website
        crawled_data = crawler.crawl(input_data.url)

        if crawled_data['pages_crawled'] == 0:
            raise HTTPException(status_code=400, detail="Failed to crawl any pages from the website")

        # Summarize text
        summary = summarize_crawled_text(crawled_data)

        result = {
            "url": crawled_data['start_url'],
            "domain": crawled_data['domain'],
            "pages_crawled": crawled_data['pages_crawled'],
            "pages": crawled_data['pages'],
            "summary": summary,
            "emails_found": crawled_data['all_emails'],
            "phones_found": crawled_data['all_phones'],
        }

        # Auto-classify if requested
        if input_data.auto_classify:
            signal = SignalInput(
                signal_text=summary,
                source_type="website_crawl",
                source_url=input_data.url,
            )

            classification_result = await classify_signal_func(signal, background_tasks, db)

            result['classification'] = {
                "lead_id": classification_result.lead_id,
                "total_score": classification_result.total_score,
                "score_bucket": classification_result.score_bucket,
                "company_name": crawled_data.get('domain'),
            }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error crawling website: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to crawl website: {str(e)}")


# ============================================================================
# Social Media Scraping
# ============================================================================

class SocialMediaSearchInput(BaseModel):
    """Input for social media search."""
    keywords: List[str]
    platform: str = "nitter"  # "linkedin", "nitter"
    location: Optional[str] = "India"
    max_results: int = 10
    auto_classify: bool = True
    filter_hiring: bool = True


@router.post("/social-media/search")
async def search_social_media(
    input_data: SocialMediaSearchInput,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Search social media for hiring posts and marketing pain signals.

    Platforms:
    - "linkedin": LinkedIn public posts (unreliable, use sparingly)
    - "nitter": Twitter via Nitter instance (more reliable)

    Args:
        keywords: Search keywords (e.g., ["hiring marketing", "marketing manager"])
        platform: Social media platform to search
        location: Location filter (for LinkedIn)
        max_results: Maximum number of results
        auto_classify: If True, classify each post as a signal
        filter_hiring: If True, filter to only hiring-related posts

    Note: Social media scraping should be used sparingly and with respect to ToS.
    For production use, use official APIs.
    """
    try:
        posts = []

        if input_data.platform == "linkedin":
            scraper = LinkedInPublicScraper()
            posts = await scraper.search_public_jobs(
                keywords=input_data.keywords,
                location=input_data.location or "India",
                max_results=input_data.max_results
            )

        elif input_data.platform == "nitter":
            scraper = NitterScraper()
            posts = await scraper.search_hiring_tweets(
                keywords=input_data.keywords,
                max_results=input_data.max_results
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {input_data.platform}")

        # Filter to hiring posts if requested
        if input_data.filter_hiring and input_data.platform == "nitter":
            posts = filter_hiring_posts(posts)

        # Auto-classify if requested
        results = []
        for post in posts:
            post_data = {
                **post,
                "status": "found",
            }

            if input_data.auto_classify:
                try:
                    # Convert post to signal text
                    signal_text = social_post_to_signal_text(post)

                    # Classify
                    signal = SignalInput(
                        signal_text=signal_text,
                        source_type=f"{input_data.platform}_post",
                        source_url=post.get('url'),
                        company_name=post.get('company'),
                    )

                    classification_result = await classify_signal_func(signal, background_tasks, db)

                    post_data['classification'] = {
                        "lead_id": classification_result.lead_id,
                        "total_score": classification_result.total_score,
                        "score_bucket": classification_result.score_bucket,
                    }
                    post_data["status"] = "classified"

                except Exception as e:
                    logger.error(f"Error classifying social media post: {e}")
                    post_data["status"] = "error"
                    post_data["error"] = str(e)

            results.append(post_data)

        return {
            "platform": input_data.platform,
            "keywords": input_data.keywords,
            "total_found": len(results),
            "classified": len([r for r in results if r.get('status') == 'classified']),
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching social media: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search social media: {str(e)}")


# ============================================================================
# Job Board API Integration
# ============================================================================

class JobBoardSearchInput(BaseModel):
    """Input for job board API search."""
    boards: List[str] = ["naukri", "linkedin"]
    keywords: List[str] = ["marketing manager", "growth hacker"]
    location: str = "India"
    max_results_per_board: int = 20
    auto_classify: bool = True


@router.post("/job-boards/api-search")
async def search_job_boards_api(
    input_data: JobBoardSearchInput,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Search job boards using their APIs (requires API credentials).

    Supported boards:
    - "naukri": Naukri.com (requires NAUKRI_API_KEY env var)
    - "linkedin": LinkedIn Jobs (requires LINKEDIN_ACCESS_TOKEN env var)

    Args:
        boards: List of boards to search
        keywords: Search keywords
        location: Job location
        max_results_per_board: Max results per board
        auto_classify: If True, classify each job as a signal

    Note: API credentials must be set in environment variables.
    """
    try:
        client = JobBoardAPIClient()

        # Fetch jobs from APIs
        jobs = await client.fetch_all_marketing_jobs(
            boards=input_data.boards,
            keywords=input_data.keywords,
            location=input_data.location,
            max_results_per_board=input_data.max_results_per_board
        )

        # Auto-classify if requested
        results = []
        for job in jobs:
            job_data = {
                "title": job.title,
                "company": job.company_name,
                "location": job.location,
                "url": job.url,
                "source_board": job.source_board,
                "status": "found",
            }

            if input_data.auto_classify:
                try:
                    # Convert job to signal text
                    signal_text = job_to_signal_text(job)

                    # Classify
                    signal = SignalInput(
                        signal_text=signal_text,
                        source_type="job_post",
                        company_name=job.company_name,
                        source_url=job.url,
                    )

                    classification_result = await classify_signal_func(signal, background_tasks, db)

                    job_data['classification'] = {
                        "lead_id": classification_result.lead_id,
                        "total_score": classification_result.total_score,
                        "score_bucket": classification_result.score_bucket,
                    }
                    job_data["status"] = "classified"

                except Exception as e:
                    logger.error(f"Error classifying job: {e}")
                    job_data["status"] = "error"
                    job_data["error"] = str(e)

            results.append(job_data)

        return {
            "boards_searched": input_data.boards,
            "keywords": input_data.keywords,
            "total_found": len(results),
            "classified": len([r for r in results if r.get('status') == 'classified']),
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error searching job boards: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search job boards: {str(e)}")


# ============================================================================
# Scheduled Tasks Management
# ============================================================================

@router.get("/scheduler/jobs")
async def list_scheduled_jobs():
    """
    List all scheduled jobs with their next run times.
    """
    try:
        jobs = get_scheduled_jobs()
        return {
            "total_jobs": len(jobs),
            "jobs": jobs,
        }
    except Exception as e:
        logger.error(f"Error listing scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/trigger/{job_id}")
async def trigger_scheduled_job(job_id: str):
    """
    Manually trigger a scheduled job to run immediately.

    Args:
        job_id: Job ID (e.g., "job_board_poll", "rss_feed_monitor")
    """
    try:
        success = trigger_job_now(job_id)

        if success:
            return {
                "message": f"Job '{job_id}' triggered successfully",
                "job_id": job_id,
            }
        else:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
