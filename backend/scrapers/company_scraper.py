"""
Company website scraper for extracting contact info and career pages
"""
import logging
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
import re
import io
import os
import shutil
import subprocess
import tempfile
from PIL import Image

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

def _ocr_image_with_tesseract(image: Image.Image, lang: str = "eng") -> str:
    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        return ""

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            temp_path = tmp.name

        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")

        image.save(temp_path, format="PNG")

        result = subprocess.run(
            [tesseract_cmd, temp_path, "stdout", "-l", lang],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return ""

        return (result.stdout or "").strip()
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


class CompanyScraper(BaseScraper):
    """Scraper for company websites to extract contact info and career pages"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.career_keywords = [
            'career', 'careers', 'jobs', 'job', 'openings', 'opportunities',
            'join-us', 'joinus', 'work-with-us', 'hiring', 'talent', 'apply'
        ]
        self.contact_keywords = [
            'contact', 'about', 'team', 'company', 'connect', 'reach'
        ]

    def scrape_company(self, url: str, deep_scan: bool = False) -> Dict[str, Any]:
        """
        Scrape company website for contact info and job postings

        Args:
            url: Company website URL
            deep_scan: If True, crawl multiple pages (slower)

        Returns:
            Dictionary with company information
        """
        company_data = {
            'url': url,
            'domain': self._get_domain(url),
            'name': None,
            'description': None,
            'emails': [],
            'phones': [],
            'people': [],
            'social_links': {},
            'career_page_url': None,
            'contact_page_url': None,
            'has_jobs': False,
            'job_signals': [],
            'technologies': [],
            'company_size_hints': []
        }

        try:
            # Fetch homepage
            response = self.fetch(url)
            if not response:
                logger.warning(f"Could not fetch {url}")
                return company_data

            response_text = response.text or ""
            lowered = response_text.lower()
            if (
                "checking your browser" in lowered
                or "cf-browser-verification" in lowered
                or "cf-challenge" in lowered
                or "cloudflare" in lowered and "attention required" in lowered
            ):
                logger.warning(f"Bot protection detected for {url}; skipping content extraction")
                return company_data

            soup = self.parse_html(response_text)

            # Extract basic company info
            basic_info = self.extract_company_info(soup, url)
            company_data.update(basic_info)

            # Get company name
            company_data['name'] = self._extract_company_name(soup, url)

            # Find career and contact page URLs
            links = self._extract_important_links(soup, url)
            company_data['career_page_url'] = links.get('career')
            company_data['contact_page_url'] = links.get('contact')

            company_data['people'].extend(self._extract_people_from_soup(soup, url))

            # Check for hiring signals on homepage
            company_data['job_signals'] = self._find_hiring_signals(soup)
            company_data['has_jobs'] = len(company_data['job_signals']) > 0

            # Extract technologies mentioned
            company_data['technologies'] = self._extract_technologies(soup)

            # Extract company size hints
            company_data['company_size_hints'] = self._extract_size_hints(soup)

            # Extract preview image (og:image) for Agent Preview
            company_data['preview_image'] = self._extract_preview_image(soup, url)

            # Run OCR on suspicious images (Agent OCR)
            ocr_text = self._scan_images_for_ocr(soup, url)
            if ocr_text:
                # Extract info from OCR text
                ocr_emails = self.extract_emails(ocr_text)
                ocr_phones = self.extract_phones(ocr_text)
                if ocr_emails:
                    company_data['emails'].extend(ocr_emails)
                    logger.info(f"OCR found emails: {ocr_emails}")
                if ocr_phones:
                    company_data['phones'].extend(ocr_phones)
                    logger.info(f"OCR found phones: {ocr_phones}")

            # If deep scan, visit career and contact pages
            if deep_scan:
                if company_data['career_page_url']:
                    career_data = self._scrape_career_page(company_data['career_page_url'])
                    company_data['emails'].extend(career_data.get('emails', []))
                    company_data['phones'].extend(career_data.get('phones', []))
                    company_data['job_signals'].extend(career_data.get('job_signals', []))
                    company_data['has_jobs'] = company_data['has_jobs'] or len(career_data.get('job_signals', [])) > 0

                if company_data['contact_page_url']:
                    contact_data = self._scrape_contact_page(company_data['contact_page_url'])
                    company_data['emails'].extend(contact_data.get('emails', []))
                    company_data['phones'].extend(contact_data.get('phones', []))
                    company_data['people'].extend(contact_data.get('people', []))

                for people_page in self._extract_people_page_urls(soup, url):
                    if people_page in {company_data.get('career_page_url'), company_data.get('contact_page_url')}:
                        continue
                    contact_data = self._scrape_contact_page(people_page)
                    company_data['emails'].extend(contact_data.get('emails', []))
                    company_data['phones'].extend(contact_data.get('phones', []))
                    company_data['people'].extend(contact_data.get('people', []))

            # Deduplicate lists
            company_data['emails'] = list(set(company_data['emails']))
            company_data['phones'] = list(set(company_data['phones']))
            dedup_people = []
            seen_people = set()
            for person in company_data.get('people') or []:
                key = (
                    (person.get('email') or '').strip().lower(),
                    (person.get('phone') or '').strip(),
                    (person.get('name') or '').strip().lower(),
                )
                if key in seen_people:
                    continue
                seen_people.add(key)
                dedup_people.append(person)
            company_data['people'] = dedup_people
            company_data['job_signals'] = list(set(company_data['job_signals']))
            company_data['technologies'] = list(set(company_data['technologies']))

            logger.info(f"Scraped company: {company_data['name']} - Found {len(company_data['emails'])} emails, {len(company_data['job_signals'])} job signals")

        except Exception as e:
            logger.error(f"Error scraping company {url}: {e}")

        return company_data

    def _extract_company_name(self, soup, url: str) -> Optional[str]:
        """Extract company name from page"""
        # Try meta tags
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            return self.clean_text(og_site['content'])

        # Try title tag
        title = soup.find('title')
        if title:
            title_text = self.clean_text(title.get_text())
            # Remove common suffixes
            for suffix in [' - Home', ' | Home', ' - Official Site', ' | Official', ' - Welcome']:
                title_text = title_text.replace(suffix, '')
            return title_text

        # Try to extract from domain
        domain = urlparse(url).netloc
        domain = domain.replace('www.', '').split('.')[0]
        return domain.capitalize()

    def _extract_important_links(self, soup, base_url: str) -> Dict[str, str]:
        """Extract career and contact page URLs"""
        links = {
            'career': None,
            'contact': None
        }

        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link['href'].lower()
            text = link.get_text().lower()

            # Make absolute URL
            full_url = urljoin(base_url, link['href'])

            # Check for career page
            if not links['career']:
                for keyword in self.career_keywords:
                    if keyword in href or keyword in text:
                        links['career'] = full_url
                        break

            # Check for contact page
            if not links['contact']:
                for keyword in self.contact_keywords:
                    if keyword in href or keyword in text:
                        links['contact'] = full_url
                        break

            if links['career'] and links['contact']:
                break

        return links

    def _extract_people_page_urls(self, soup, base_url: str) -> List[str]:
        urls: List[str] = []
        for link in soup.find_all('a', href=True):
            href = (link.get('href') or '').strip()
            if not href:
                continue
            href_l = href.lower()
            text_l = (link.get_text() or '').strip().lower()
            if any(k in href_l or k in text_l for k in ('contact', 'team', 'about', 'leadership', 'founder', 'management')):
                full_url = urljoin(base_url, href)
                urls.append(full_url)
        deduped = []
        seen = set()
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            deduped.append(u)
        return deduped[:3]

    def _extract_people_from_soup(self, soup, source_url: str) -> List[Dict[str, Any]]:
        people: List[Dict[str, Any]] = []
        blocks = soup.find_all(['section', 'div', 'li', 'article', 'p'])

        name_re = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b")
        role_re = re.compile(
            r"\b(Founder|Co-?Founder|CEO|CTO|CMO|COO|CFO|VP|Vice President|Director|Head|Manager|Marketing|Growth|Sales)\b",
            re.IGNORECASE,
        )

        for block in blocks:
            text = (block.get_text(" ", strip=True) or "").strip()
            if not text:
                continue
            emails = self.extract_emails(text)
            phones = self.extract_phones(text)
            if not emails or not phones:
                continue

            name = None
            for tag in block.find_all(['h1', 'h2', 'h3', 'strong', 'b', 'span']):
                cand = (tag.get_text(" ", strip=True) or "").strip()
                if not cand:
                    continue
                if len(cand) > 80:
                    continue
                if '@' in cand:
                    continue
                if any(word in cand.lower() for word in ('contact', 'email', 'phone', 'call', 'write to', 'reach')):
                    continue
                m = name_re.search(cand)
                if m:
                    name = m.group(0).strip()
                    break

            if not name:
                m = name_re.search(text)
                if m:
                    name = m.group(0).strip()

            role = None
            m_role = role_re.search(text)
            if m_role:
                role = m_role.group(0).strip()

            email = (emails[0] or '').strip()
            phone = (phones[0] or '').strip()
            if not (name and email and phone):
                continue

            people.append({
                'name': name,
                'role': role,
                'email': email,
                'phone': phone,
                'source_url': source_url,
            })

        if people:
            return people

        # Fallback (still compliant): if the page has explicit email + phone anywhere,
        # pair them with the best page-level name candidate (or "Contact Team").
        page_text = (soup.get_text(" ", strip=True) or "").strip()
        page_emails = self.extract_emails(page_text)
        page_phones = self.extract_phones(page_text)
        if page_emails and page_phones:
            candidate_name = None
            for tag in soup.find_all(['h1', 'h2', 'h3', 'strong']):
                cand = (tag.get_text(" ", strip=True) or "").strip()
                if not cand or len(cand) > 80:
                    continue
                if any(word in cand.lower() for word in ('contact', 'reach', 'connect', 'support', 'sales', 'team')):
                    candidate_name = cand
                    break
                m = name_re.search(cand)
                if m:
                    candidate_name = m.group(0).strip()
                    break

            if not candidate_name:
                candidate_name = "Contact Team"

            people.append({
                'name': candidate_name,
                'role': None,
                'email': (page_emails[0] or '').strip(),
                'phone': (page_phones[0] or '').strip(),
                'source_url': source_url,
            })

        return people

    def _find_hiring_signals(self, soup) -> List[str]:
        """Find hiring/job-related signals on page"""
        signals = []
        page_text = soup.get_text().lower()

        # Hiring keywords
        hiring_patterns = [
            r"we['\u2019]re hiring",
            r"we are hiring",
            r"join our team",
            r"careers",
            r"job opening",
            r"positions? available",
            r"apply now",
            r"looking for",
            r"seeking",
            r"hiring for",
            r"recruitment",
            r"grow our team",
            r"expanding team"
        ]

        for pattern in hiring_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                # Get context around match (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(page_text), match.end() + 100)
                context = page_text[start:end].strip()
                if context:
                    signals.append(self.clean_text(context))

        # Look for job titles in headings
        job_title_patterns = [
            r'\b(hiring|seeking|looking for).{0,20}(manager|developer|engineer|designer|marketer|analyst|lead)',
            r'\b(manager|developer|engineer|designer|marketer|analyst|lead).{0,20}(wanted|needed|required)',
        ]

        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong'])
        for heading in headings:
            heading_text = heading.get_text().lower()
            for pattern in job_title_patterns:
                if re.search(pattern, heading_text, re.IGNORECASE):
                    signals.append(self.clean_text(heading.get_text()))

        return signals[:10]  # Limit to 10 most relevant signals

    def _extract_technologies(self, soup) -> List[str]:
        """Extract technologies/tools mentioned on website"""
        page_text = soup.get_text().lower()

        tech_keywords = [
            # Programming languages
            'python', 'javascript', 'java', 'ruby', 'php', 'go', 'golang', 'rust',
            'typescript', 'kotlin', 'swift', 'c++', 'c#', 'scala',
            # Frameworks
            'react', 'angular', 'vue', 'django', 'flask', 'rails', 'laravel',
            'node.js', 'express', 'spring', 'fastapi',
            # Databases
            'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch',
            # Cloud/DevOps
            'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes',
            'terraform', 'jenkins', 'gitlab', 'github',
            # Marketing tools
            'hubspot', 'salesforce', 'marketo', 'mailchimp', 'google analytics',
            'facebook ads', 'google ads', 'shopify', 'wordpress'
        ]

        found_tech = []
        for tech in tech_keywords:
            if tech in page_text:
                found_tech.append(tech)

        return found_tech

    def _extract_size_hints(self, soup) -> List[str]:
        """Extract hints about company size"""
        page_text = soup.get_text().lower()
        hints = []

        size_patterns = [
            (r'(\d+)\+?\s*(employees?|people|team members?)', 'employees'),
            (r'team of (\d+)', 'team_size'),
            (r'(\d+)\s*person (company|team|startup)', 'team_size'),
            (r'(solo|one person|founder|solopreneur)', 'solo'),
            (r'(small team|small company|startup)', 'small'),
            (r'(growing team|scaling|expanding)', 'growing'),
        ]

        for pattern, hint_type in size_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                hints.append(match.group(0))

        return hints[:5]

    def _extract_preview_image(self, soup, url: str) -> Optional[str]:
        """Extract og:image or first large image as preview"""
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return urljoin(url, og_image['content'])
        
        # Fallback: Find a logo or large image
        # Heuristic: Image with 'logo' in class or id
        logo = soup.find('img', class_=re.compile(r'logo', re.I))
        if logo and logo.get('src'):
            return urljoin(url, logo['src'])
            
        return None

    def _scan_images_for_ocr(self, soup, base_url: str) -> str:
        """Scan images that might contain text (contact info) and run OCR"""
        ocr_results = []
        
        # Find images that look like they might have contact info
        # e.g. filename contains 'email', 'contact', 'phone'
        images = soup.find_all('img', src=True)
        target_images = []
        
        for img in images:
            src = img['src'].lower()
            if any(k in src for k in ['email', 'contact', 'phone', 'mail', 'call']):
                full_url = urljoin(base_url, img['src'])
                target_images.append(full_url)
                
        # Also check for images in contact sections
        contact_section = soup.find('div', class_=re.compile(r'contact|footer', re.I))
        if contact_section:
            for img in contact_section.find_all('img', src=True):
                full_url = urljoin(base_url, img['src'])
                if full_url not in target_images:
                    target_images.append(full_url)

        # Limit OCR to avoid slowness
        for img_url in target_images[:3]:
            try:
                # Download image
                response = self.fetch(img_url)
                if response:
                    image = Image.open(io.BytesIO(response.content))
                    # Run OCR
                    text = _ocr_image_with_tesseract(image)
                    if len(text.strip()) > 5:
                        ocr_results.append(text)
                        logger.info(f"OCR extracted text from {img_url}")
            except Exception as e:
                logger.warning(f"OCR failed for {img_url}: {e}")
                
        return "\n".join(ocr_results)

    def _scrape_career_page(self, url: str) -> Dict[str, Any]:
        """Scrape career/jobs page for detailed information"""
        data = {
            'emails': [],
            'phones': [],
            'job_signals': []
        }

        try:
            response = self.fetch(url)
            if not response:
                return data

            soup = self.parse_html(response.text)

            # Extract contact info
            page_text = soup.get_text()
            data['emails'] = self.extract_emails(page_text)
            data['phones'] = self.extract_phones(page_text)

            # Find job postings/signals
            data['job_signals'] = self._find_hiring_signals(soup)

            # Look for job titles
            job_title_elements = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
            for elem in job_title_elements:
                text = self.clean_text(elem.get_text())
                # Check if looks like a job title
                if 5 < len(text) < 100:  # Reasonable length
                    job_keywords = ['manager', 'developer', 'engineer', 'designer', 'analyst',
                                  'specialist', 'coordinator', 'director', 'lead', 'head']
                    if any(keyword in text.lower() for keyword in job_keywords):
                        data['job_signals'].append(text)

        except Exception as e:
            logger.error(f"Error scraping career page {url}: {e}")

        return data

    def _scrape_contact_page(self, url: str) -> Dict[str, Any]:
        """Scrape contact/about page for contact information"""
        data = {
            'emails': [],
            'phones': [],
            'people': [],
        }

        try:
            response = self.fetch(url)
            if not response:
                return data

            soup = self.parse_html(response.text)
            page_text = soup.get_text()

            data['emails'] = self.extract_emails(page_text)
            data['phones'] = self.extract_phones(page_text)
            data['people'] = self._extract_people_from_soup(soup, url)

        except Exception as e:
            logger.error(f"Error scraping contact page {url}: {e}")

        return data


class LeadDiscoveryScraper(BaseScraper):
    """
    Scraper for discovering new leads via search engines
    """

    def _extract_duckduckgo_results_from_soup(
        self,
        soup: BeautifulSoup,
        num_results: int,
        source: str,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        # DuckDuckGo endpoints have multiple HTML variants.
        # Prefer known containers but fall back to broader selectors.
        candidates: List[Any] = []
        candidates.extend(soup.find_all('div', class_='result'))
        candidates.extend(soup.find_all('div', class_='results_links'))
        candidates.extend(soup.find_all('tr'))

        def _push_result(title_link, snippet_text: str | None):
            if not title_link:
                return
            title = self.clean_text(title_link.get_text() or "")
            raw_href = title_link.get('href')
            url = self._normalize_duckduckgo_result_url(raw_href)
            if not (title and url):
                return
            results.append(
                {
                    'title': title,
                    'url': url,
                    'snippet': self.clean_text(snippet_text) if snippet_text else None,
                    'source': source,
                }
            )

        # Variant A: html.duckduckgo.com
        for div in soup.find_all('div', class_='result'):
            if len(results) >= num_results:
                break
            title_link = div.find('a', class_='result__a') or div.find('a', class_='result__url')
            snippet_elem = (
                div.find('a', class_='result__snippet')
                or div.find('div', class_='result__snippet')
                or div.find('span', class_='result__snippet')
            )
            _push_result(title_link, snippet_elem.get_text() if snippet_elem else None)

        if len(results) >= num_results:
            return results[:num_results]

        # Variant B: lite.duckduckgo.com
        for a in soup.select('a.result-link'):
            if len(results) >= num_results:
                break
            snippet_text = None
            tr = a.find_parent('tr')
            if tr:
                snippet_cell = tr.find('td', class_='result-snippet')
                if snippet_cell:
                    snippet_text = snippet_cell.get_text()
            _push_result(a, snippet_text)

        if len(results) >= num_results:
            return results[:num_results]

        # Variant C: last-resort generic anchors (avoid DDG internal nav)
        for a in soup.find_all('a'):
            if len(results) >= num_results:
                break
            href = (a.get('href') or '').strip()
            if not href:
                continue
            if 'duckduckgo.com' in href and '/l/' not in href:
                continue
            title = self.clean_text(a.get_text() or "")
            if not title or len(title) < 3:
                continue
            _push_result(a, None)

        return results[:num_results]

    def _normalize_duckduckgo_result_url(self, href: str) -> str | None:
        if not href:
            return None

        href = href.strip()
        if not href:
            return None

        try:
            from urllib.parse import urlparse, parse_qs, unquote, urljoin

            # DuckDuckGo sometimes returns protocol-relative URLs
            if href.startswith("//"):
                href = f"https:{href}"

            # DuckDuckGo HTML sometimes returns relative redirect links
            if href.startswith("/"):
                href = urljoin("https://duckduckgo.com", href)

            parsed = urlparse(href)

            # Decode redirect target if present
            if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
                qs = parse_qs(parsed.query)
                uddg = qs.get("uddg", [None])[0]
                if uddg:
                    target = unquote(uddg)
                    if target.startswith("//"):
                        target = f"https:{target}"
                    if target.startswith("http://") or target.startswith("https://"):
                        return target

            # Otherwise ensure it is an absolute URL
            if href.startswith("http://") or href.startswith("https://"):
                return href

        except Exception:
            return None

        return None

    def search_for_leads(self, query: str, num_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for potential leads using Google/Bing

        Args:
            query: Search query (e.g., "D2C ecommerce India hiring marketing")
            num_results: Number of results to return

        Returns:
            List of potential lead URLs and snippets
        """
        leads = []

        # Try DuckDuckGo (easier to scrape than Google)
        try:
            leads = self._search_duckduckgo(query, num_results)
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")

        return leads

    def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search DuckDuckGo (less restrictive than Google)"""
        results = []

        try:
            from urllib.parse import quote_plus
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

            response = self.fetch(search_url)
            if not response:
                return results

            soup = self.parse_html(response.text)

            results = self._extract_duckduckgo_results_from_soup(
                soup=soup,
                num_results=num_results,
                source='duckduckgo_html',
            )

            # Fallback: DuckDuckGo lite endpoint (often more stable than html).
            if not results:
                lite_url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
                lite_resp = self.fetch(lite_url)
                if lite_resp:
                    lite_soup = self.parse_html(lite_resp.text)
                    results = self._extract_duckduckgo_results_from_soup(
                        soup=lite_soup,
                        num_results=num_results,
                        source='duckduckgo_lite',
                    )

        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {e}")

        return results
