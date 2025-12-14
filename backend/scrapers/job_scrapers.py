"""
Job board scrapers for lead generation using Headless Playwright
"""
import logging
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote_plus
import re

from .base_scraper import BaseScraper
from .headless_scraper import HeadlessScraper

logger = logging.getLogger(__name__)


class JobBoardScraper(HeadlessScraper):
    """Generic job board scraper using HeadlessScraper"""

    def scrape_jobs(self, query: str, location: str = "", num_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape jobs from job board (to be implemented by subclasses)

        Args:
            query: Search query (e.g., "marketing manager")
            location: Location filter
            num_pages: Number of pages to scrape

        Returns:
            List of job dictionaries
        """
        raise NotImplementedError("Subclasses must implement scrape_jobs()")

    def extract_job_details(self, job_elem) -> Dict[str, Any]:
        """Extract job details from job element"""
        raise NotImplementedError("Subclasses must implement extract_job_details()")


class IndeedScraper(JobBoardScraper):
    """Scraper for Indeed.com job postings"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.indeed.com"

    def scrape_jobs(self, query: str, location: str = "", num_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Indeed using Playwright

        Args:
            query: Job search query
            location: Location filter
            num_pages: Number of pages to scrape

        Returns:
            List of job postings with company info
        """
        jobs = []

        for page in range(num_pages):
            start = page * 10
            params = {
                'q': query,
                'l': location,
                'start': start
            }

            search_url = f"{self.base_url}/jobs?{urlencode(params)}"

            try:
                # Use Playwright to fetch content
                html_content = self.fetch_page_content(search_url, wait_for_selector=".job_seen_beacon")
                
                if not html_content:
                    logger.warning(f"Failed to fetch Indeed page {page}")
                    continue

                soup = self.parse_html(html_content)

                # Find job cards
                job_cards = soup.find_all('div', class_=lambda x: x and 'job_seen_beacon' in x)
                
                if not job_cards:
                    # Try alternative selector
                    job_cards = soup.find_all('td', class_='resultContent')

                for card in job_cards:
                    try:
                        job = self._extract_indeed_job(card)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Error extracting Indeed job: {e}")
                        continue
                
                # Random delay between pages
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.error(f"Error scraping Indeed page {page}: {e}")
                continue

        logger.info(f"Scraped {len(jobs)} jobs from Indeed")
        return jobs

    def _extract_indeed_job(self, card) -> Optional[Dict[str, Any]]:
        """Extract job details from Indeed job card"""
        job = {
            'title': None,
            'company': None,
            'location': None,
            'description': None,
            'url': None,
            'source': 'indeed'
        }

        # Title
        title_elem = card.find('h2', class_='jobTitle')
        if not title_elem:
            title_elem = card.find('a', class_=lambda x: x and 'jcs-JobTitle' in x)
            
        if title_elem:
            job['title'] = self.clean_text(title_elem.get_text())

        # Company
        company_elem = card.find('span', {'data-testid': 'company-name'})
        if company_elem:
            job['company'] = self.clean_text(company_elem.get_text())

        # Location
        location_elem = card.find('div', {'data-testid': 'text-location'})
        if location_elem:
            job['location'] = self.clean_text(location_elem.get_text())

        # Description snippet
        desc_elem = card.find('div', class_='job-snippet')
        if desc_elem:
            job['description'] = self.clean_text(desc_elem.get_text())

        # Job URL
        link_elem = card.find('a', class_=lambda x: x and 'jcs-JobTitle' in str(x))
        if link_elem and link_elem.get('href'):
            job['url'] = self.base_url + link_elem['href']
            # Fix relative URL
            if not job['url'].startswith('http'):
                 job['url'] = self.base_url + '/' + link_elem['href'].lstrip('/')


        # Only return if we have minimum info
        if job['title'] and job['company']:
            return job
        return None


class NaukriScraper(JobBoardScraper):
    """Scraper for Naukri.com (Indian job board)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.naukri.com"

    def scrape_jobs(self, query: str, location: str = "", num_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Naukri using Playwright

        Args:
            query: Job search query
            location: Location filter
            num_pages: Number of pages to scrape

        Returns:
            List of job postings
        """
        jobs = []

        for page in range(1, num_pages + 1):
            # Naukri URL format
            query_slug = quote_plus(query)
            search_url = f"{self.base_url}/{query_slug}-jobs"
            if location:
                search_url += f"-in-{quote_plus(location)}"
            
            if page > 1:
                search_url += f"-{page}"

            try:
                # Naukri requires JS rendering
                html_content = self.fetch_page_content(search_url, wait_for_selector=".srp-jobtuple-wrapper")
                
                if not html_content:
                    continue

                soup = self.parse_html(html_content)

                # Find job cards (Naukri structure)
                # Updated selector for Naukri's latest UI
                job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')
                
                if not job_cards:
                    # Fallback to older selectors just in case
                    job_cards = soup.find_all('article', class_='jobTuple')

                for card in job_cards:
                    try:
                        job = self._extract_naukri_job(card)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Error extracting Naukri job: {e}")
                        continue
                
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.error(f"Error scraping Naukri page {page}: {e}")
                continue

        logger.info(f"Scraped {len(jobs)} jobs from Naukri")
        return jobs

    def _extract_naukri_job(self, card) -> Optional[Dict[str, Any]]:
        """Extract job details from Naukri job card"""
        job = {
            'title': None,
            'company': None,
            'location': None,
            'description': None,
            'experience': None,
            'salary': None,
            'url': None,
            'source': 'naukri'
        }

        # Title
        title_elem = card.find('a', class_='title')
        if title_elem:
            job['title'] = self.clean_text(title_elem.get_text())
            if title_elem.get('href'):
                job['url'] = title_elem['href']

        # Company
        company_elem = card.find('a', class_='comp-name')
        if company_elem:
            job['company'] = self.clean_text(company_elem.get_text())

        # Location
        location_elem = card.find('span', class_='locWdth')
        if location_elem:
            job['location'] = self.clean_text(location_elem.get_text())

        # Experience
        exp_elem = card.find('span', class_='expwdth')
        if exp_elem:
            job['experience'] = self.clean_text(exp_elem.get_text())

        # Salary
        salary_elem = card.find('span', class_='sal-wrap')
        if salary_elem:
            job['salary'] = self.clean_text(salary_elem.get_text())

        # Description - Usually hidden in list view, but sometimes snippet exists
        # Naukri structure varies, sometimes description is in row tags
        
        # Only return if we have minimum info
        if job['title'] and job['company']:
            return job
        return None


class LinkedInJobsScraper(JobBoardScraper):
    """
    LinkedIn Jobs scraper using Playwright
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.linkedin.com"

    def scrape_jobs(self, query: str, location: str = "", num_pages: int = 2) -> List[Dict[str, Any]]:
        """
        Scrape jobs from LinkedIn Jobs (public) using Playwright
        """
        jobs = []

        for page in range(num_pages):
            start = page * 25
            params = {
                'keywords': query,
                'location': location,
                'start': start,
                'trk': 'public_jobs_jobs-search-bar_search-submit'
            }

            search_url = f"{self.base_url}/jobs/search?{urlencode(params)}"

            try:
                # LinkedIn requires more realistic headers and interactions
                # We wait for the job list to load
                html_content = self.fetch_page_content(search_url, wait_for_selector=".jobs-search__results-list")
                
                if not html_content:
                    logger.warning(f"Failed to fetch LinkedIn page {page}")
                    continue

                soup = self.parse_html(html_content)

                # Find job cards
                job_cards = soup.find_all('li')
                
                # Filter for actual job cards
                valid_cards = []
                for card in job_cards:
                     if card.find('div', class_='base-card'):
                         valid_cards.append(card)
                     elif card.find('a', class_='base-card__full-link'):
                         valid_cards.append(card)

                for card in valid_cards:
                    try:
                        job = self._extract_linkedin_job(card)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Error extracting LinkedIn job: {e}")
                        continue
                
                time.sleep(random.uniform(3, 7))

            except Exception as e:
                logger.error(f"Error scraping LinkedIn page {page}: {e}")
                continue

        logger.info(f"Scraped {len(jobs)} jobs from LinkedIn")
        return jobs

    def _extract_linkedin_job(self, card) -> Optional[Dict[str, Any]]:
        """Extract job details from LinkedIn job card"""
        job = {
            'title': None,
            'company': None,
            'location': None,
            'description': None,
            'url': None,
            'source': 'linkedin'
        }

        # Title
        title_elem = card.find('h3', class_='base-search-card__title')
        if title_elem:
            job['title'] = self.clean_text(title_elem.get_text())

        # Company
        company_elem = card.find('h4', class_='base-search-card__subtitle')
        if company_elem:
            job['company'] = self.clean_text(company_elem.get_text())

        # Location
        location_elem = card.find('span', class_='job-search-card__location')
        if location_elem:
            job['location'] = self.clean_text(location_elem.get_text())

        # URL
        link_elem = card.find('a', class_='base-card__full-link')
        if link_elem and link_elem.get('href'):
            job['url'] = link_elem['href']

        # Only return if we have minimum info
        if job['title'] and job['company']:
            return job
        return None


class GenericJobScraper(BaseScraper):
    """
    Generic scraper that attempts to find job postings on any career page
    Note: Generic scraper keeps using BaseScraper (Requests) for speed on static sites,
    but could be upgraded to HeadlessScraper if needed.
    """

    def scrape_career_page(self, url: str) -> List[Dict[str, Any]]:
        """
        Attempt to scrape jobs from a generic career/jobs page

        Args:
            url: URL of career page

        Returns:
            List of job postings found
        """
        jobs = []

        try:
            response = self.fetch(url)
            if not response:
                return jobs

            soup = self.parse_html(response.text)

            # Look for common job listing patterns
            job_patterns = [
                {'tag': 'div', 'class': re.compile(r'job|position|opening|vacancy', re.I)},
                {'tag': 'li', 'class': re.compile(r'job|position|opening', re.I)},
                {'tag': 'article', 'class': re.compile(r'job|position', re.I)},
                {'tag': 'div', 'class': re.compile(r'career', re.I)},
            ]

            potential_jobs = []
            for pattern in job_patterns:
                elements = soup.find_all(pattern['tag'], class_=pattern['class'])
                potential_jobs.extend(elements)

            # Extract job information
            for elem in potential_jobs[:50]:  # Limit to first 50 to avoid noise
                job = self._extract_generic_job(elem, url)
                if job:
                    jobs.append(job)

            logger.info(f"Scraped {len(jobs)} jobs from {url}")

        except Exception as e:
            logger.error(f"Error scraping career page {url}: {e}")

        return jobs

    def _extract_generic_job(self, elem, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract job info from a generic element"""
        job = {
            'title': None,
            'description': None,
            'url': base_url,
            'source': 'career_page'
        }

        # Try to find title in various tag types
        title_elem = elem.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
        if title_elem:
            title_text = self.clean_text(title_elem.get_text())
            # Filter out very short or very long titles
            if 5 < len(title_text) < 100:
                job['title'] = title_text

        # Get description from element text
        desc_text = self.clean_text(elem.get_text())
        if len(desc_text) > 50:  # Must have substantial text
            job['description'] = desc_text[:500]  # Limit length

        # Try to find a more specific URL
        link = elem.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('http'):
                job['url'] = href
            elif href.startswith('/'):
                from urllib.parse import urljoin
                job['url'] = urljoin(base_url, href)

        # Only return if we have a title
        if job['title']:
            return job
        return None
