"""
Scraping orchestration service - coordinates all scrapers and processes results
"""
import logging
import signal
import time
import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from .job_scrapers import IndeedScraper, NaukriScraper, LinkedInJobsScraper, GenericJobScraper
from .company_scraper import CompanyScraper, LeadDiscoveryScraper
from .enhanced_scrapers import SocialScraper, NewsScraper, TechStackScraper
from .startup_scrapers import YCombinatorScraper, CustomSourceScraper
from database import Company, Contact, Signal, Lead, SessionLocal
from ollama_wrapper import classify_signal_with_ollama
from event_bus import event_bus
from lead_upsert import upsert_lead

logger = logging.getLogger(__name__)

def log_agent_event(agent: str, message: str, type: str = "info", image_url: str = None):
    """Emit an agent log event to the event bus"""
    data = {
        "agent": agent,
        "message": message,
        "type": type,
        "timestamp": datetime.now().isoformat()
    }
    if image_url:
        data["image_url"] = image_url

    event_bus.publish_sync({
        "type": "mission_log",
        "data": data
    })

@contextmanager
def timeout_context(seconds: int):
    """Context manager for timeout with signal-based interruption"""
    sigalrm = getattr(signal, "SIGALRM", None)
    alarm = getattr(signal, "alarm", None)
    if sigalrm is None or alarm is None or threading.current_thread() is not threading.main_thread():
        yield
        return

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set the timeout handler
    signal.signal(sigalrm, timeout_handler)
    alarm(seconds)

    try:
        yield
    finally:
        # Clear the alarm
        alarm(0)

def scrape_with_timeout(scraper_method: Callable, timeout_seconds: int = 30, *args, **kwargs) -> List[Dict]:
    """Execute scraper method with timeout protection"""
    try:
        with timeout_context(timeout_seconds):
            return scraper_method(*args, **kwargs)
    except TimeoutError:
        logger.error(f"Scraper timed out after {timeout_seconds}s: {scraper_method.__name__}")
        return []
    except Exception as e:
        logger.error(f"Scraper failed: {scraper_method.__name__} - {e}")
        return []

def scrape_with_retry(scraper_method: Callable, max_attempts: int = 3, base_timeout: int = 30, *args, **kwargs) -> List[Dict]:
    """Retry scraper with exponential backoff and increasing timeouts"""
    for attempt in range(max_attempts):
        try:
            # Increase timeout for each retry
            timeout_seconds = base_timeout * (2 ** attempt)  # 30s, 60s, 120s
            logger.info(f"Attempt {attempt + 1}/{max_attempts} for {scraper_method.__name__} (timeout: {timeout_seconds}s)")

            result = scrape_with_timeout(scraper_method, timeout_seconds, *args, **kwargs)

            if result:  # Only return if we got results
                logger.info(f"Scraper succeeded on attempt {attempt + 1}")
                return result
            else:
                logger.warning(f"Scraper returned empty results on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    sleep_time = 2 ** attempt  # 1s, 2s, 4s backoff
                    logger.info(f"Waiting {sleep_time}s before retry...")
                    time.sleep(sleep_time)
                continue

        except Exception as e:
            if attempt < max_attempts - 1:
                sleep_time = 2 ** attempt
                logger.warning(f"Scraper failed, retrying in {sleep_time}s: {e}")
                time.sleep(sleep_time)
                continue
            logger.error(f"Scraper failed after {max_attempts} attempts: {e}")
            raise e

    logger.error(f"No results after {max_attempts} attempts")
    return []


class ScrapingService:
    """
    Orchestrates scraping operations and processes results
    Enhanced for maximum lead discovery and deep research
    """

    def __init__(self):
        # Initialize scrapers with respect_robots=False to ensure they work aggressively as requested
        self.indeed_scraper = IndeedScraper(rate_limit=2.0, respect_robots=False)
        self.naukri_scraper = NaukriScraper(rate_limit=2.0, respect_robots=False)
        self.linkedin_scraper = LinkedInJobsScraper(rate_limit=3.0, respect_robots=False)  # Slower for LinkedIn
        self.company_scraper = CompanyScraper(rate_limit=2.0, respect_robots=False)
        self.lead_discovery = LeadDiscoveryScraper(rate_limit=2.0, respect_robots=False)
        self.generic_job_scraper = GenericJobScraper(rate_limit=2.0, respect_robots=False)
        # Startup and Custom scrapers
        self.yc_scraper = YCombinatorScraper(rate_limit=2.0, respect_robots=False)
        self.custom_scraper = CustomSourceScraper(rate_limit=2.0, respect_robots=False)
        # Enhanced scrapers for deep research
        self.social_scraper = SocialScraper(rate_limit=5.0, respect_robots=False)  # Faster for social
        self.news_scraper = NewsScraper(rate_limit=3.0, respect_robots=False)
        self.tech_stack_scraper = TechStackScraper(rate_limit=2.0, respect_robots=False)
        self.executor = ThreadPoolExecutor(max_workers=5)  # More concurrent tasks

    def scrape_job_boards(
        self,
        query: str,
        location: str = "",
        sources: List[str] = None,
        num_pages: int = 3
    ) -> Dict[str, Any]:
        """
        Scrape multiple job boards and process results

        Args:
            query: Job search query (e.g., "marketing manager")
            location: Location filter
            sources: List of sources to scrape ['indeed', 'naukri', 'linkedin'] or None for all
            num_pages: Number of pages per source

        Returns:
            Dictionary with scraping results and stats
        """
        if sources is None:
            sources = ['indeed', 'naukri']  # Exclude LinkedIn by default (more restrictive)

        results = {
            'query': query,
            'location': location,
            'started_at': datetime.now().isoformat(),
            'sources': {},
            'total_jobs': 0,
            'total_leads_created': 0,
            'errors': []
        }

        all_jobs = []

        # Scrape each source
        for source in sources:
            try:
                logger.info(f"Scraping {source} for: {query}")
                jobs = []

                if source == 'indeed':
                    jobs = scrape_with_retry(
                        self.indeed_scraper.scrape_jobs,
                        max_attempts=3,
                        base_timeout=45,
                        query=query,
                        location=location,
                        num_pages=num_pages
                    )
                elif source == 'naukri':
                    jobs = scrape_with_retry(
                        self.naukri_scraper.scrape_jobs,
                        max_attempts=3,
                        base_timeout=45,
                        query=query,
                        location=location,
                        num_pages=num_pages
                    )
                elif source == 'linkedin':
                    jobs = scrape_with_retry(
                        self.linkedin_scraper.scrape_jobs,
                        max_attempts=2,  # LinkedIn is stricter
                        base_timeout=60,  # LinkedIn needs more time
                        query=query,
                        location=location,
                        num_pages=num_pages
                    )

                results['sources'][source] = {
                    'jobs_found': len(jobs),
                    'status': 'success'
                }

                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs from {source}")

            except Exception as e:
                logger.error(f"Error scraping {source}: {e}")
                results['sources'][source] = {
                    'jobs_found': 0,
                    'status': 'error',
                    'error': str(e)
                }
                results['errors'].append(f"{source}: {str(e)}")

        results['total_jobs'] = len(all_jobs)

        # Process and store jobs
        try:
            leads_created = self._process_job_postings(all_jobs)
            results['total_leads_created'] = leads_created
        except Exception as e:
            logger.error(f"Error processing job postings: {e}")
            results['errors'].append(f"Processing error: {str(e)}")

        results['completed_at'] = datetime.now().isoformat()
        return results

    def scrape_company_website(
        self,
        url: str,
        company_name: Optional[str] = None,
        deep_scan: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape a company website for contact info and job signals

        Args:
            url: Company website URL
            company_name: Optional company name (will be extracted if not provided)
            deep_scan: If True, crawl career and contact pages

        Returns:
            Dictionary with company data and scraping results
        """
        results = {
            'url': url,
            'started_at': datetime.now().isoformat(),
            'company_data': None,
            'leads_created': 0,
            'error': None
        }

        try:
            logger.info(f"Scraping company website: {url}")
            company_data = self.company_scraper.scrape_company(url, deep_scan)

            if company_name:
                company_data['name'] = company_name

            results['company_data'] = company_data

            # Process company data and create leads if hiring signals found
            if company_data.get('has_jobs') or company_data.get('job_signals'):
                leads_created = self._process_company_data(company_data)
                results['leads_created'] = leads_created

        except Exception as e:
            logger.error(f"Error scraping company website {url}: {e}")
            results['error'] = str(e)

        results['completed_at'] = datetime.now().isoformat()
        return results

    def discover_leads(
        self,
        search_query: str,
        num_results: int = 20,
        scrape_companies: bool = False,
        deep_scan: bool = False
    ) -> Dict[str, Any]:
        """
        Discover new leads via search engines

        Args:
            search_query: Search query (e.g., "D2C ecommerce India hiring")
            num_results: Number of search results to fetch
            scrape_companies: If True, also scrape each discovered company website
            deep_scan: If True, perform deep scan on company websites (Obsessive Mode)

        Returns:
            Dictionary with discovered leads
        """
        results = {
            'query': search_query,
            'started_at': datetime.now().isoformat(),
            'urls_found': 0,
            'companies_scraped': 0,
            'leads_created': 0,
            'discovered_urls': [],
            'errors': []
        }

        try:
            # Search for leads
            logger.info(f"Discovering leads with query: {search_query}")
            log_agent_event("Search Agent", f"Searching for '{search_query}' via DuckDuckGo...", "info")
            
            search_results = self.lead_discovery.search_for_leads(search_query, num_results)

            results['urls_found'] = len(search_results)
            results['discovered_urls'] = [r['url'] for r in search_results]
            
            log_agent_event("Search Agent", f"Found {len(search_results)} potential company URLs matching criteria.", "success")

            # Optionally scrape each discovered company
            if scrape_companies:
                for result in search_results:
                    try:
                        company_url = result['url']
                        logger.info(f"Scraping discovered company: {company_url}")
                        log_agent_event("Scrape Agent", f"Scraping {company_url} for signals...", "info")

                        company_result = self.scrape_company_website(
                            company_url,
                            deep_scan=deep_scan
                        )
                        
                        # Get preview image
                        preview_image = company_result['company_data'].get('preview_image')
                        
                        found_emails = len(company_result['company_data'].get('emails', []))
                        found_signals = len(company_result['company_data'].get('job_signals', []))
                        
                        if found_emails > 0 or found_signals > 0:
                            log_agent_event("Scrape Agent", f"Found {found_emails} emails and {found_signals} signals on {company_url}.", "success", image_url=preview_image)
                        else:
                            log_agent_event("Scrape Agent", f"No significant signals found on {company_url}.", "warning", image_url=preview_image)

                        results['companies_scraped'] += 1
                        results['leads_created'] += company_result.get('leads_created', 0)

                    except Exception as e:
                        logger.error(f"Error scraping discovered company {company_url}: {e}")
                        log_agent_event("Scrape Agent", f"Failed to scrape {result['url']}: {str(e)}", "error")
                        results['errors'].append(f"{company_url}: {str(e)}")

        except Exception as e:
            logger.error(f"Error discovering leads: {e}")
            log_agent_event("Search Agent", f"Search failed: {str(e)}", "error")
            results['errors'].append(str(e))

        results['completed_at'] = datetime.now().isoformat()
        return results

    def scrape_career_page(self, url: str, company_name: str) -> Dict[str, Any]:
        """
        Scrape a specific career/jobs page

        Args:
            url: Career page URL
            company_name: Company name

        Returns:
            Dictionary with jobs found and leads created
        """
        results = {
            'url': url,
            'company_name': company_name,
            'started_at': datetime.now().isoformat(),
            'jobs_found': 0,
            'leads_created': 0,
            'error': None
        }

        try:
            logger.info(f"Scraping career page: {url}")
            jobs = self.generic_job_scraper.scrape_career_page(url)

            results['jobs_found'] = len(jobs)

            # Add company name to each job
            for job in jobs:
                job['company'] = company_name

            # Process jobs
            if jobs:
                leads_created = self._process_job_postings(jobs)
                results['leads_created'] = leads_created

        except Exception as e:
            logger.error(f"Error scraping career page {url}: {e}")
            results['error'] = str(e)

        results['completed_at'] = datetime.now().isoformat()
        return results

    def scrape_startup_listings(self, source: str = "ycombinator", query: str = "") -> Dict[str, Any]:
        """
        Scrape startup listings (e.g. YCombinator)

        Args:
            source: Source name ('ycombinator')
            query: Search query

        Returns:
            Dictionary with companies found and leads created
        """
        results = {
            'source': source,
            'query': query,
            'started_at': datetime.now().isoformat(),
            'companies_found': 0,
            'leads_created': 0,
            'error': None
        }

        try:
            logger.info(f"Scraping startup listings from {source} for {query}")
            companies = []
            
            if source == "ycombinator":
                companies = self.yc_scraper.scrape_listings(query, limit=20)
            else:
                raise ValueError(f"Unknown startup source: {source}")

            results['companies_found'] = len(companies)

            # Process companies
            # For startups, we create a company record and maybe a lead if description looks good
            # Or we trigger a deep website scrape
            
            leads_created = 0
            db = SessionLocal()
            
            try:
                for comp in companies:
                    # Get or create company
                    db_comp = self._get_or_create_company(
                        db, 
                        name=comp['name'], 
                        website=comp.get('website')
                    )
                    
                    if comp.get('description'):
                        # Add description to company
                        db_comp.description = comp['description']
                        db_comp.company_metadata = {**(db_comp.company_metadata or {}), 'source': source}
                        db.flush()
                        
                        # Create signal
                        signal_text = f"Startup Listing ({source}): {comp['name']}\n{comp['description']}"
                        signal = Signal(
                            company_id=db_comp.id,
                            raw_text=signal_text,
                            source_type='startup_listing',
                            source_url=comp.get('profile_url')
                        )
                        db.add(signal)
                        db.flush()
                        
                        # Classify
                        try:
                            classification = classify_signal_with_ollama(
                                signal_text=signal_text,
                                company_name=comp['name'],
                                company_website=comp.get('website')
                            )
                            
                            if classification and classification.get('icp_match'):
                                lead = self._create_lead_from_classification(
                                    db, db_comp, signal, classification
                                )
                                if lead:
                                    leads_created += 1
                        except Exception as e:
                            logger.error(f"Error classifying startup {comp['name']}: {e}")
                            
                db.commit()
                results['leads_created'] = leads_created
                
            except Exception as e:
                logger.error(f"Error processing startup companies: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error scraping startup listings: {e}")
            results['error'] = str(e)

        results['completed_at'] = datetime.now().isoformat()
        return results

    def scrape_custom_urls(self, urls: List[str]) -> Dict[str, Any]:
        """
        Scrape a list of custom URLs

        Args:
            urls: List of URLs to scrape

        Returns:
            Dictionary with results
        """
        results = {
            'urls_count': len(urls),
            'started_at': datetime.now().isoformat(),
            'processed': 0,
            'leads_created': 0,
            'error': None
        }
        
        try:
            logger.info(f"Scraping {len(urls)} custom URLs")
            scraped_data = self.custom_scraper.scrape_url_list(urls)
            results['processed'] = len(scraped_data)
            
            # Process as company data
            for data in scraped_data:
                if data:
                    leads = self._process_company_data(data)
                    results['leads_created'] += leads
                    
        except Exception as e:
            logger.error(f"Error scraping custom URLs: {e}")
            results['error'] = str(e)
            
        results['completed_at'] = datetime.now().isoformat()
        return results

    def shutdown(self):
        """Cleanup resources"""
        logger.info("Shutting down scraping service...")
        try:
            if hasattr(self.indeed_scraper, 'close'):
                self.indeed_scraper.close()
            if hasattr(self.naukri_scraper, 'close'):
                self.naukri_scraper.close()
            if hasattr(self.linkedin_scraper, 'close'):
                self.linkedin_scraper.close()
            if hasattr(self.yc_scraper, 'close'):
                self.yc_scraper.close()
            if hasattr(self.custom_scraper, 'close'):
                self.custom_scraper.close()
            self.executor.shutdown(wait=False)
            logger.info("Scraping service shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down scraping service: {e}")

    def _process_job_postings(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Process job postings and create leads

        Args:
            jobs: List of job dictionaries

        Returns:
            Number of leads created
        """
        leads_created = 0
        db = SessionLocal()

        try:
            for job in jobs:
                try:
                    company_name = job.get('company')
                    if not company_name:
                        continue

                    # Get or create company
                    company = self._get_or_create_company(db, company_name, None, job.get('location'))

                    # Create signal from job posting
                    signal_text = self._format_job_signal(job)

                    # Check for duplicate signals
                    existing_signal = db.query(Signal).filter(
                        Signal.company_id == company.id,
                        Signal.raw_text == signal_text
                    ).first()

                    if existing_signal:
                        logger.debug(f"Duplicate signal for {company_name}, skipping")
                        continue

                    # Create signal
                    signal = Signal(
                        company_id=company.id,
                        raw_text=signal_text,
                        source_type='job_post',
                        source_url=job.get('url')
                    )
                    db.add(signal)
                    db.flush()

                    # Classify signal and create lead
                    try:
                        classification = classify_signal_with_ollama(
                            signal_text=signal_text,
                            company_name=company_name,
                            company_website=company.website
                        )

                        if classification and classification.get('icp_match'):
                            # Create lead
                            lead = self._create_lead_from_classification(
                                db, company, signal, classification
                            )
                            if lead:
                                leads_created += 1

                    except Exception as e:
                        logger.error(f"Error classifying signal for {company_name}: {e}")

                except Exception as e:
                    logger.error(f"Error processing job posting for {company_name} ({job.get('url')}): {e}")
                    continue

            db.commit()

        except Exception as e:
            logger.error(f"Error in _process_job_postings: {e}")
            db.rollback()
        finally:
            db.close()

        return leads_created

    def _process_company_data(self, company_data: Dict[str, Any]) -> int:
        """
        Process company data and create leads from hiring signals

        Args:
            company_data: Company data dictionary

        Returns:
            Number of leads created
        """
        leads_created = 0
        db = SessionLocal()

        try:
            company_name = company_data.get('name')
            company_url = company_data.get('url')

            if not company_name:
                return 0

            # Get or create company before attaching contacts/signals
            company = self._get_or_create_company(
                db,
                name=company_name,
                website=company_url
            )

            # Create ONLY complete person contacts (name + email + phone).
            for person in (company_data.get('people') or [])[:10]:
                try:
                    name = (person.get('name') or '').strip()
                    email = (person.get('email') or '').strip()
                    phone = (person.get('phone') or '').strip()
                    role = (person.get('role') or '').strip() or None
                    if not (name and email and phone):
                        continue
                    self._get_or_create_contact(
                        db,
                        company,
                        contact_name=name,
                        role=role,
                        email=email,
                        phone=phone,
                    )
                except Exception:
                    continue

            # Process job signals
            for job_signal in company_data.get('job_signals', []):
                try:
                    # Check for duplicate
                    existing_signal = db.query(Signal).filter(
                        Signal.company_id == company.id,
                        Signal.raw_text == job_signal
                    ).first()

                    if existing_signal:
                        continue

                    # Create signal
                    signal = Signal(
                        company_id=company.id,
                        raw_text=job_signal,
                        source_type='website',
                        source_url=company_url
                    )
                    db.add(signal)
                    db.flush()

                    # Classify and create lead
                    try:
                        classification = classify_signal_with_ollama(
                            signal_text=job_signal,
                            company_name=company_name,
                            company_website=company_url
                        )

                        if classification:
                            score = classification.get('total_score', 0)
                            bucket = classification.get('score_bucket', 'parked')
                            log_agent_event("Extraction Agent", f"Classified signal from {company_name}: Score {score} ({bucket})", "info")

                        if classification and classification.get('icp_match'):
                            people = company_data.get('people') or []
                            if not people:
                                log_agent_event(
                                    "Extraction Agent",
                                    f"Skipped lead creation for {company_name}: no complete person contact (name+email+phone).",
                                    "warning",
                                )
                                continue

                            created_any = False
                            for person in people[:5]:
                                contact_name = (person.get('name') or '').strip()
                                email = (person.get('email') or '').strip()
                                phone = (person.get('phone') or '').strip()
                                role = (person.get('role') or '').strip() or None
                                if not (contact_name and email and phone):
                                    continue

                                lead = self._create_lead_from_classification(
                                    db,
                                    company,
                                    signal,
                                    classification,
                                    contact_name=contact_name,
                                    role=role,
                                    email=email,
                                    phone=phone,
                                )
                                if lead:
                                    created_any = True
                                    leads_created += 1
                                    log_agent_event(
                                        "Extraction Agent",
                                        f"✅ Lead created for {company_name} ({contact_name}) (Score: {classification.get('total_score')})",
                                        "success",
                                    )
                                    break

                            if created_any and classification.get('total_score', 0) > 70:
                                log_agent_event(
                                    "Reasoning Agent",
                                    f"High value lead detected. Queuing deep dossier generation for {company_name}...",
                                    "info",
                                )

                    except Exception as e:
                        logger.error(f"Error classifying signal: {e}")
                        log_agent_event("Extraction Agent", f"Classification failed: {str(e)}", "error")

                except Exception as e:
                    logger.error(f"Error processing job signal for {company_name}: {e}")
                    continue

            db.commit()

        except Exception as e:
            logger.error(f"Error in _process_company_data: {e}")
            db.rollback()
        finally:
            db.close()

        return leads_created

    def _get_or_create_company(
        self,
        db: Session,
        name: str,
        website: Optional[str] = None,
        city: Optional[str] = None
    ) -> Company:
        """Get or create company record"""
        # Try to find existing company
        query = db.query(Company)

        if website:
            # Try by website first
            company = query.filter(Company.website == website).first()
            if company:
                if city and not company.city: # Update city if missing
                    company.city = city
                    db.flush()
                return company

        # Try by name (case-insensitive)
        company = query.filter(Company.name.ilike(name)).first()
        if company:
            # Update website if provided and not set
            if website and not company.website:
                company.website = website
                db.flush()
            if city and not company.city: # Update city if missing
                company.city = city
                db.flush()
            return company

        # Create new company
        company = Company(
            name=name,
            website=website,
            city=city
        )
        db.add(company)
        db.flush()
        return company

    def _get_or_create_contact(
        self,
        db: Session,
        company: Company,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        contact_name: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Optional[Contact]:
        """Get or create contact record"""
        if not email and not phone:
            return None

        normalized_email = email.strip().lower() if email else None
        normalized_phone = phone.strip() if phone else None

        # Try to find existing
        query = db.query(Contact).filter(Contact.company_id == company.id)

        if normalized_email:
            contact = query.filter(Contact.email.ilike(normalized_email)).first()
            if contact:
                changed = False
                if contact_name and not contact.name:
                    contact.name = contact_name
                    changed = True
                if role and not contact.role:
                    contact.role = role
                    changed = True
                if normalized_phone:
                    phone_numbers = contact.phone_numbers or []
                    if not isinstance(phone_numbers, list):
                        phone_numbers = [phone_numbers]
                    if normalized_phone not in phone_numbers:
                        phone_numbers.append(normalized_phone)
                        contact.phone_numbers = phone_numbers
                        changed = True
                if changed:
                    db.flush()
                return contact

        if normalized_phone:
            candidates = query.all()
            for candidate in candidates:
                phone_numbers = candidate.phone_numbers or []
                if isinstance(phone_numbers, dict):
                    phone_values = list(phone_numbers.values())
                elif isinstance(phone_numbers, list):
                    phone_values = phone_numbers
                else:
                    phone_values = [phone_numbers]
                if any((isinstance(v, str) and v.strip() == normalized_phone) for v in phone_values if v):
                    contact = candidate
                    break
            else:
                contact = None

            if contact:
                changed = False
                if normalized_email and not contact.email:
                    contact.email = normalized_email
                    changed = True
                phone_numbers = contact.phone_numbers or []
                if not isinstance(phone_numbers, list):
                    phone_numbers = [phone_numbers]
                if normalized_phone not in phone_numbers:
                    phone_numbers.append(normalized_phone)
                    contact.phone_numbers = phone_numbers
                    changed = True
                if changed:
                    db.flush()
                return contact

        # Create new
        contact = Contact(
            company_id=company.id,
            name=contact_name,
            role=role,
            email=normalized_email,
            phone_numbers=[normalized_phone] if normalized_phone else []
        )
        db.add(contact)
        db.flush()
        return contact

    def _create_lead_from_classification(
        self,
        db: Session,
        company: Company,
        signal: Signal,
        classification: Dict[str, Any],
        contact_name: Optional[str] = None,
        role: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[Lead]:
        """Create lead from classification results"""
        try:
            # Only pass columns that actually exist on the Lead model
            allowed_fields = {
                "score_icp_fit",
                "score_marketing_pain",
                "score_data_quality",
                "total_score",
                "score_bucket",
                "icp_matches",
                "role_type",
                "pain_tags",
                "situation",
                "problem",
                "implication",
                "need_payoff",
                "economic_buyer_guess",
                "key_pain",
                "chaos_flags",
                "silver_bullet_phrases",
                "context_dossier",
                "challenger_insight",
                "reframe_suggestion",
                "status",
                "owner",
                "notes",
            }

            filtered_classification = {
                key: value for key, value in classification.items() if key in allowed_fields
            }

            # Check if lead already exists for this company
            result = upsert_lead(
                db,
                company_name=company.name,
                company_website=company.website,
                contact_name=contact_name,
                role=role,
                email=email,
                phone=phone,
                lead_fields=filtered_classification,
                update_existing=True,
                require_contact=True,
            )

            lead = result.get("lead")
            status = result.get("status")

            if lead is not None and signal is not None:
                signal.lead_id = lead.id
                db.add(signal)
                db.flush()

            # Notify frontend
            if status in {"created", "updated"}:
                return lead
            return None

        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            return None

    def _format_job_signal(self, job: Dict[str, Any]) -> str:
        """Format job posting as signal text"""
        parts = []

        if job.get('title'):
            parts.append(f"Job Title: {job['title']}")

        if job.get('company'):
            parts.append(f"Company: {job['company']}")

        if job.get('location'):
            parts.append(f"Location: {job['location']}")

        if job.get('description'):
            parts.append(f"Description: {job['description']}")

        if job.get('experience'):
            parts.append(f"Experience: {job['experience']}")

        if job.get('salary'):
            parts.append(f"Salary: {job['salary']}")

        return "\n".join(parts)


# Global instance
scraping_service = ScrapingService()
