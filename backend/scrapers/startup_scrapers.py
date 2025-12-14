"""
Startup listing and community forum scrapers
"""
import logging
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from .headless_scraper import HeadlessScraper

logger = logging.getLogger(__name__)

class StartupListingScraper(HeadlessScraper):
    """Base class for startup directory scrapers"""
    
    def scrape_listings(self, query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape startup listings"""
        raise NotImplementedError

class YCombinatorScraper(StartupListingScraper):
    """Scraper for Y Combinator companies"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.ycombinator.com/companies"

    def scrape_listings(self, query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """
        Scrape YC companies
        
        Args:
            query: Search term (e.g., "B2B", "AI")
            limit: Max number of companies to return
        """
        start_url = self.base_url
        if query:
            start_url += f"?query={query}"
            
        companies = []
        
        try:
            # YC uses dynamic loading (infinite scroll or pagination)
            html = self.fetch_page_content(start_url, wait_for_selector=".create-profile")
            # .create-profile is just a guess, usually we look for company cards
            # Actually YC classes are often obfuscated or semantic like '_company_86jzd_338'
            # But link to company usually contains /companies/
            
            if not html:
                return []
                
            soup = self.parse_html(html)
            
            # Find company links
            # Strategy: Find links containing '/companies/' that are not the base url
            links = soup.find_all('a', href=True)
            company_links = set()
            
            for link in links:
                href = link['href']
                if '/companies/' in href and href != '/companies':
                    full_url = urljoin("https://www.ycombinator.com", href)
                    company_links.add(full_url)
                    
            logger.info(f"Found {len(company_links)} potential YC companies")
            
            # Visit each company page to get details (limiting to 'limit')
            for url in list(company_links)[:limit]:
                try:
                    company = self._scrape_yc_company_details(url)
                    if company:
                        companies.append(company)
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    logger.error(f"Error scraping YC company {url}: {e}")
                    
        except Exception as e:
            logger.error(f"Error scraping YC listings: {e}")
            
        return companies

    def _scrape_yc_company_details(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract details from YC company page"""
        html = self.fetch_page_content(url)
        if not html:
            return None
            
        soup = self.parse_html(html)
        
        company = {
            'name': None,
            'description': None,
            'website': None,
            'location': None,
            'source': 'ycombinator',
            'profile_url': url
        }
        
        # Name
        h1 = soup.find('h1')
        if h1:
            company['name'] = self.clean_text(h1.get_text())
            
        # Website - usually an external link icon or text
        # Look for common patterns or external links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'ycombinator.com' not in href and href.startswith('http'):
                # Candidate for website, usually the first one in header
                # Heuristic: Often has class 'website-link' or similar, or just location
                # For now, simple heuristic: first external link in main content
                company['website'] = href
                break
                
        # Description
        # Look for meta description or paragraph
        desc = soup.find('div', class_=lambda x: x and 'description' in x)
        if not desc:
            desc = soup.find('p') # Fallback
            
        if desc:
            company['description'] = self.clean_text(desc.get_text())
            
        if company['name']:
            return company
        return None

class ProductHuntScraper(StartupListingScraper):
    """Scraper for Product Hunt (Example)"""
    # Implementation would go here, similar structure
    pass

class CustomSourceScraper(HeadlessScraper):
    """Scraper for a list of custom URLs (forums, blogs, etc.)"""
    
    def scrape_url_list(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape a provided list of URLs for company info and leads
        """
        results = []
        for url in urls:
            try:
                info = self.scrape_page(url)
                if info:
                    results.append(info)
            except Exception as e:
                logger.error(f"Error scraping custom URL {url}: {e}")
        return results

    def scrape_page(self, url: str) -> Dict[str, Any]:
        """Generic page scrape for signals"""
        html = self.fetch_page_content(url)
        if not html:
            return {}
            
        soup = self.parse_html(html)
        info = self.extract_company_info(soup, url)
        
        # Also look for "hiring" signals specifically
        text = soup.get_text().lower()
        hiring_keywords = ['hiring', 'careers', 'jobs', 'join us', 'open positions']
        info['hiring_signals'] = [k for k in hiring_keywords if k in text]
        
        return info
