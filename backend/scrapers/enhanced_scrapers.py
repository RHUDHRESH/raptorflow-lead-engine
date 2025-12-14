"""
Enhanced scrapers for deep lead research and intelligence gathering
"""
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime, timedelta

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SocialScraper(BaseScraper):
    """
    Scrapes social media profiles for lead intelligence
    Focus: LinkedIn, Twitter, company social presence
    """

    def __init__(self, rate_limit: float = 5.0, respect_robots: bool = True):
        super().__init__(rate_limit=rate_limit, respect_robots=respect_robots)

    def scrape_linkedin_profile(self, profile_url: str) -> Dict[str, Any]:
        """Scrape LinkedIn profile for professional intelligence"""
        try:
            response = self.fetch(profile_url)
            if not response:
                return {}

            soup = self.parse_html(response.text)
            data = {
                'url': profile_url,
                'name': self._extract_linkedin_name(soup),
                'title': self._extract_linkedin_title(soup),
                'company': self._extract_linkedin_company(soup),
                'location': self._extract_linkedin_location(soup),
                'about': self._extract_linkedin_about(soup),
                'experience': self._extract_linkedin_experience(soup),
                'connections': self._extract_linkedin_connections(soup),
                'posts': self._extract_recent_posts(soup),
                'scraped_at': datetime.now().isoformat()
            }
            return data
        except Exception as e:
            logger.error(f"Error scraping LinkedIn profile {profile_url}: {e}")
            return {}

    def scrape_twitter_profile(self, handle: str) -> Dict[str, Any]:
        """Scrape Twitter profile for social signals"""
        try:
            url = f"https://twitter.com/{handle}"
            response = self.fetch(url)
            if not response:
                return {}

            soup = self.parse_html(response.text)
            data = {
                'handle': handle,
                'name': self._extract_twitter_name(soup),
                'bio': self._extract_twitter_bio(soup),
                'location': self._extract_twitter_location(soup),
                'website': self._extract_twitter_website(soup),
                'joined_date': self._extract_twitter_joined(soup),
                'following': self._extract_twitter_following(soup),
                'followers': self._extract_twitter_followers(soup),
                'recent_tweets': self._extract_recent_tweets(soup)
            }
            return data
        except Exception as e:
            logger.error(f"Error scraping Twitter profile {handle}: {e}")
            return {}

    def _extract_linkedin_name(self, soup):
        """Extract name from LinkedIn profile"""
        selectors = ['h1.text-heading-xlarge', '.pv-text-details__left-panel h1']
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def _extract_linkedin_title(self, soup):
        """Extract current job title"""
        element = soup.select_one('.pv-text-details__left-panel .text-body-medium')
        return element.get_text(strip=True) if element else None

    def _extract_linkedin_company(self, soup):
        """Extract current company"""
        element = soup.select_one('.pv-text-details__right-panel .text-body-small')
        return element.get_text(strip=True) if element else None

    def _extract_linkedin_location(self, soup):
        """Extract location"""
        element = soup.select_one('.pv-text-details__left-panel .text-body-small')
        return element.get_text(strip=True) if element else None

    def _extract_linkedin_about(self, soup):
        """Extract about section"""
        element = soup.select_one('.pv-about__summary-text')
        return element.get_text(strip=True) if element else None

    def _extract_linkedin_experience(self, soup):
        """Extract work experience"""
        experiences = []
        exp_elements = soup.select('.pv-entity__summary-info h3')
        for exp in exp_elements[:3]:  # Top 3 experiences
            experiences.append(exp.get_text(strip=True))
        return experiences

    def _extract_linkedin_connections(self, soup):
        """Extract number of connections"""
        element = soup.select_one('.pv-top-card__connections')
        if element:
            text = element.get_text(strip=True)
            # Extract number from "500+ connections"
            match = re.search(r'(\d+\+?)', text)
            return match.group(1) if match else text
        return None

    def _extract_recent_posts(self, soup):
        """Extract recent activity"""
        posts = []
        post_elements = soup.select('.feed-shared-update-v2')[:5]
        for post in post_elements:
            text_element = post.select_one('.feed-shared-text')
            if text_element:
                posts.append(text_element.get_text(strip=True)[:200])
        return posts

    def _extract_twitter_name(self, soup):
        """Extract Twitter display name"""
        element = soup.select_one('[data-testid="User-Name"]')
        return element.get_text(strip=True) if element else None

    def _extract_twitter_bio(self, soup):
        """Extract Twitter bio"""
        element = soup.select_one('[data-testid="User-Description"]')
        return element.get_text(strip=True) if element else None

    def _extract_twitter_location(self, soup):
        """Extract Twitter location"""
        element = soup.select_one('[data-testid="User-Location"]')
        return element.get_text(strip=True) if element else None

    def _extract_twitter_website(self, soup):
        """Extract Twitter website"""
        element = soup.select_one('[data-testid="User-Website"] a')
        return element.get('href') if element else None

    def _extract_twitter_joined(self, soup):
        """Extract Twitter join date"""
        element = soup.select_one('[data-testid="User-Professional-User-Text"]')
        return element.get_text(strip=True) if element else None

    def _extract_twitter_following(self, soup):
        """Extract following count"""
        element = soup.select_one('[role="link"][href*="following"] [dir="ltr"]')
        return element.get_text(strip=True) if element else None

    def _extract_twitter_followers(self, soup):
        """Extract followers count"""
        element = soup.select_one('[role="link"][href*="followers"] [dir="ltr"]')
        return element.get_text(strip=True) if element else None

    def _extract_recent_tweets(self, soup):
        """Extract recent tweets"""
        tweets = []
        tweet_elements = soup.select('[data-testid="Tweet-User-Text"]')[:3]
        for tweet in tweet_elements:
            tweets.append(tweet.get_text(strip=True)[:300])
        return tweets


class NewsScraper(BaseScraper):
    """
    Scrapes news and press releases for company intelligence
    Sources: TechCrunch, YourStory, Inc42, Business Standard, etc.
    """

    def __init__(self, rate_limit: float = 3.0, respect_robots: bool = True):
        super().__init__(rate_limit=rate_limit, respect_robots=respect_robots)
        self.sources = {
            'techcrunch': 'https://techcrunch.com/search/',
            'yourstory': 'https://yourstory.com/search/',
            'inc42': 'https://inc42.com/search/',
            'business_standard': 'https://www.business-standard.com/search?q='
        }

    def search_company_news(self, company_name: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Search for recent company news across multiple sources"""
        all_news = []
        since_date = datetime.now() - timedelta(days=days_back)

        for source_name, base_url in self.sources.items():
            try:
                news_items = self._scrape_source_news(source_name, base_url, company_name, since_date)
                all_news.extend(news_items)
            except Exception as e:
                logger.error(f"Error scraping {source_name}: {e}")

        # Sort by date and remove duplicates
        all_news.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
        seen = set()
        deduped = []
        for item in all_news:
            title = item.get('title', '').lower()
            if title not in seen:
                seen.add(title)
                deduped.append(item)

        return deduped[:20]  # Top 20 most recent/relevant

    def _scrape_source_news(self, source_name: str, base_url: str, company_name: str, since_date: datetime) -> List[Dict[str, Any]]:
        """Scrape news from a specific source"""
        news_items = []

        try:
            # Build search URL
            if 'techcrunch' in source_name:
                search_url = f"{base_url}{company_name.replace(' ', '%20')}"
            elif 'business_standard' in source_name:
                search_url = f"{base_url}{company_name.replace(' ', '%20')}"
            else:
                search_url = f"{base_url}{company_name.replace(' ', '-')}/"

            response = self.fetch(search_url)
            if not response:
                return news_items

            soup = self.parse_html(response.text)

            if source_name == 'techcrunch':
                news_items.extend(self._extract_techcrunch_news(soup, since_date))
            elif source_name == 'yourstory':
                news_items.extend(self._extract_yourstory_news(soup, since_date))
            elif source_name == 'inc42':
                news_items.extend(self._extract_inc42_news(soup, since_date))
            elif source_name == 'business_standard':
                news_items.extend(self._extract_business_standard_news(soup, since_date))

        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")

        return news_items

    def _extract_techcrunch_news(self, soup, since_date):
        """Extract news from TechCrunch search results"""
        news = []
        articles = soup.select('article')

        for article in articles:
            title_elem = article.select_one('h2 a')
            date_elem = article.select_one('time')
            summary_elem = article.select_one('.post-block__content')

            if title_elem:
                date = self._parse_date(date_elem.get('datetime') if date_elem else None)
                if date and date >= since_date:
                    news.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href'),
                        'date': date,
                        'summary': summary_elem.get_text(strip=True) if summary_elem else '',
                        'source': 'TechCrunch'
                    })

        return news

    def _extract_yourstory_news(self, soup, since_date):
        """Extract news from YourStory"""
        news = []
        articles = soup.select('.story-item')

        for article in articles:
            title_elem = article.select_one('.story-title a')
            date_elem = article.select_one('.story-date')

            if title_elem:
                date = self._parse_date(date_elem.get_text(strip=True) if date_elem else None)
                if date and date >= since_date:
                    news.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href'),
                        'date': date,
                        'summary': '',
                        'source': 'YourStory'
                    })

        return news

    def _extract_inc42_news(self, soup, since_date):
        """Extract news from Inc42"""
        news = []
        articles = soup.select('.card')

        for article in articles:
            title_elem = article.select_one('h2 a')
            date_elem = article.select_one('.date')

            if title_elem:
                date = self._parse_date(date_elem.get_text(strip=True) if date_elem else None)
                if date and date >= since_date:
                    news.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href'),
                        'date': date,
                        'summary': '',
                        'source': 'Inc42'
                    })

        return news

    def _extract_business_standard_news(self, soup, since_date):
        """Extract news from Business Standard"""
        news = []
        articles = soup.select('.listing-item')

        for article in articles:
            title_elem = article.select_one('h2 a')
            date_elem = article.select_one('.date')

            if title_elem:
                date = self._parse_date(date_elem.get_text(strip=True) if date_elem else None)
                if date and date >= since_date:
                    summary_elem = article.select_one('.listing-excerpt')
                    news.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href'),
                        'date': date,
                        'summary': summary_elem.get_text(strip=True) if summary_elem else '',
                        'source': 'Business Standard'
                    })

        return news

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_str:
            return None

        try:
            # Handle common formats: ISO, "2 days ago", "Dec 15, 2024"
            if 'ago' in date_str.lower():
                return self._parse_relative_date(date_str)

            # Try ISO format first
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                pass

            # Try common formats
            for fmt in ['%b %d, %Y', '%B %d, %Y', '%d %b %Y', '%Y-%m-%d']:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue

            # Default to today if parsing fails
            return datetime.now()

        except Exception:
            return None

    def _parse_relative_date(self, date_str: str) -> datetime:
        """Parse relative dates like '2 days ago'"""
        now = datetime.now()

        if 'day' in date_str:
            days = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(days=days)
        elif 'hour' in date_str:
            hours = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(hours=hours)
        elif 'week' in date_str:
            weeks = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(weeks=weeks)
        else:
            return now


class TechStackScraper(BaseScraper):
    """
    Detects technology stack and tools used by companies
    Methods: BuiltWith, Wappalyzer-style detection, common indicators
    """

    def __init__(self, rate_limit: float = 2.0, respect_robots: bool = True):
        super().__init__(rate_limit=rate_limit, respect_robots=respect_robots)
        self.tech_patterns = {
            'wordpress': [r'wp-content', r'wp-includes', r'wordpress'],
            'shopify': [r'cdn\.shopify\.com', r'shopify'],
            'woocommerce': [r'woocommerce', r'wp-content/plugins/woocommerce'],
            'magento': [r'var/cache', r'magento'],
            'react': [r'react', r'__REACT_DEVTOOLS_GLOBAL_HOOK__'],
            'vue': [r'vue', r'__VUE__'],
            'angular': [r'angular', r'ng-version'],
            'bootstrap': [r'bootstrap', r'bootstrapcdn'],
            'tailwind': [r'tailwind', r'tailwindcss'],
            'analytics': {
                'google_analytics': r'google\.analytics',
                'facebook_pixel': r'facebook\.com/tr',
                'hotjar': r'hotjar',
                'mixpanel': r'mixpanel',
                'segment': r'segment\.com'
            },
            'crm': {
                'hubspot': r'hubspot',
                'salesforce': r'salesforce',
                'pipedrive': r'pipedrive',
                'zoho': r'zoho',
                'freshworks': r'freshworks'
            },
            'email': {
                'mailchimp': r'mailchimp',
                'sendgrid': r'sendgrid',
                'aws_ses': r'aws\.amazon\.com/ses',
                'postmark': r'postmark'
            }
        }

    def detect_tech_stack(self, website_url: str) -> Dict[str, Any]:
        """Detect technology stack from website analysis"""
        try:
            response = self.fetch(website_url)
            if not response:
                return {'url': website_url, 'error': 'Could not fetch website'}

            soup = self.parse_html(response.text)
            html_content = response.text

            tech_stack = {
                'url': website_url,
                'platform': self._detect_platform(html_content),
                'framework': self._detect_framework(html_content),
                'styling': self._detect_styling(html_content),
                'analytics': self._detect_analytics(html_content, soup),
                'crm': self._detect_crm(html_content, soup),
                'email': self._detect_email(html_content, soup),
                'other_tools': self._detect_other_tools(html_content, soup),
                'estimated_monthly_traffic': self._estimate_traffic(website_url),
                'detected_at': datetime.now().isoformat()
            }

            return tech_stack

        except Exception as e:
            logger.error(f"Error detecting tech stack for {website_url}: {e}")
            return {'url': website_url, 'error': str(e)}

    def _detect_platform(self, html_content: str) -> Optional[str]:
        """Detect e-commerce/CMS platform"""
        for platform, patterns in self.tech_patterns.items():
            if isinstance(patterns, list):
                for pattern in patterns:
                    if re.search(pattern, html_content, re.IGNORECASE):
                        return platform

        # Check meta tags
        if 'generator' in html_content.lower():
            if 'wordpress' in html_content.lower():
                return 'wordpress'
            elif 'shopify' in html_content.lower():
                return 'shopify'

        return None

    def _detect_framework(self, html_content: str) -> Optional[str]:
        """Detect JavaScript framework"""
        frameworks = ['react', 'vue', 'angular']
        for framework in frameworks:
            patterns = self.tech_patterns[framework]
            for pattern in patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    return framework
        return None

    def _detect_styling(self, html_content: str) -> Optional[str]:
        """Detect CSS framework"""
        if re.search(r'tailwind', html_content, re.IGNORECASE):
            return 'tailwind'
        elif re.search(r'bootstrap', html_content, re.IGNORECASE):
            return 'bootstrap'
        return None

    def _detect_analytics(self, html_content: str, soup) -> List[str]:
        """Detect analytics tools"""
        analytics = []
        for tool, pattern in self.tech_patterns['analytics'].items():
            if re.search(pattern, html_content, re.IGNORECASE):
                analytics.append(tool.replace('_', ' ').title())

        # Check for Google Tag Manager
        if re.search(r'googletagmanager', html_content, re.IGNORECASE):
            analytics.append('Google Tag Manager')

        return analytics

    def _detect_crm(self, html_content: str, soup) -> List[str]:
        """Detect CRM tools"""
        crm = []
        for tool, pattern in self.tech_patterns['crm'].items():
            if re.search(pattern, html_content, re.IGNORECASE):
                crm.append(tool.replace('_', ' ').title())
        return crm

    def _detect_email(self, html_content: str, soup) -> List[str]:
        """Detect email service providers"""
        email = []
        for tool, pattern in self.tech_patterns['email'].items():
            if re.search(pattern, html_content, re.IGNORECASE):
                email.append(tool.replace('_', ' ').title())
        return email

    def _detect_other_tools(self, html_content: str, soup) -> List[str]:
        """Detect other business tools"""
        tools = []

        # Payment processors
        if re.search(r'stripe|razorpay|payu|instamojo', html_content, re.IGNORECASE):
            tools.append('Payment Processing')

        # Chat widgets
        if re.search(r'intercom|zendesk|freshchat|tawk\.to', html_content, re.IGNORECASE):
            tools.append('Live Chat')

        # SEO tools
        if re.search(r'ahrefs|semrush|moz', html_content, re.IGNORECASE):
            tools.append('SEO Tools')

        return tools

    def _estimate_traffic(self, url: str) -> Optional[str]:
        """Estimate monthly traffic (rough heuristic)"""
        try:
            # This would normally use external APIs, but we'll do heuristics
            domain = urlparse(url).netloc

            # Check for common high-traffic indicators
            response = self.fetch(url)
            if response:
                # Simple traffic estimation based on tech stack and content
                content_size = len(response.text)

                if 'shopify' in response.text.lower():
                    return '10k-100k'  # Shopify stores often have decent traffic
                elif 'wordpress' in response.text.lower():
                    return '1k-50k'
                elif content_size > 500000:  # Large content sites
                    return '5k-50k'
                else:
                    return '500-10k'

        except Exception:
            pass

        return None
