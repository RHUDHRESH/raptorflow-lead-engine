"""
Adaptive Scraper Selection engine that intelligently chooses scraping methods.
Analyzes targets and selects optimal scraping strategy for maximum success rate.
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable, Type
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

class ScraperMethod(Enum):
    """Available scraping methods"""
    REQUESTS_DIRECT = "requests_direct"  # Fastest, basic HTTP requests
    HEADLESS_BROWSER = "headless_browser"  # Full JavaScript support
    API_REVERSE = "api_reverse"  # API endpoints if available
    MOBILE_EMULATION = "mobile_emulation"  # Mobile user agents
    PROXY_CHAIN = "proxy_chain"  # Multiple proxy hops
    STEALTH_MODE = "stealth_mode"  # Maximum evasion techniques

class TargetDifficulty(Enum):
    """Target site difficulty levels"""
    EASY = "easy"  # Basic sites, no protection
    MEDIUM = "medium"  # Some JavaScript, basic anti-bot
    HARD = "hard"  # Heavy JavaScript, Cloudflare, etc.
    EXTREME = "extreme"  # Advanced anti-bot systems

@dataclass
class TargetAnalysis:
    """Analysis of a scraping target"""
    url: str
    domain: str
    difficulty: TargetDifficulty
    requires_javascript: bool
    has_api_endpoints: bool
    uses_cloudflare: bool
    rate_limit_detected: bool
    content_type: str  # 'static', 'dynamic', 'spa'
    estimated_success_rate: float
    recommended_method: ScraperMethod
    fallback_methods: List[ScraperMethod]

@dataclass
class ScraperCapability:
    """Capabilities of a scraper method"""
    method: ScraperMethod
    supports_javascript: bool
    supports_apis: bool
    supports_mobile: bool
    stealth_level: int  # 1-10, higher is more stealthy
    speed_rating: int  # 1-10, higher is faster
    success_rate: float  # Estimated success rate
    resource_usage: int  # 1-10, higher uses more resources

class AdaptiveScraper:
    """
    Intelligently selects optimal scraping methods based on target analysis
    """
    
    def __init__(self):
        self.target_cache: Dict[str, TargetAnalysis] = {}
        self.cache_expiry = 3600  # 1 hour
        
        # Define scraper capabilities
        self.scraper_capabilities = {
            ScraperMethod.REQUESTS_DIRECT: ScraperCapability(
                method=ScraperMethod.REQUESTS_DIRECT,
                supports_javascript=False,
                supports_apis=True,
                supports_mobile=False,
                stealth_level=2,
                speed_rating=10,
                success_rate=0.9,
                resource_usage=1
            ),
            ScraperMethod.HEADLESS_BROWSER: ScraperCapability(
                method=ScraperMethod.HEADLESS_BROWSER,
                supports_javascript=True,
                supports_apis=True,
                supports_mobile=True,
                stealth_level=7,
                speed_rating=4,
                success_rate=0.95,
                resource_usage=6
            ),
            ScraperMethod.API_REVERSE: ScraperCapability(
                method=ScraperMethod.API_REVERSE,
                supports_javascript=False,
                supports_apis=True,
                supports_mobile=True,
                stealth_level=8,
                speed_rating=9,
                success_rate=0.98,
                resource_usage=2
            ),
            ScraperMethod.MOBILE_EMULATION: ScraperCapability(
                method=ScraperMethod.MOBILE_EMULATION,
                supports_javascript=True,
                supports_apis=True,
                supports_mobile=True,
                stealth_level=6,
                speed_rating=5,
                resource_usage=5
            ),
            ScraperMethod.PROXY_CHAIN: ScraperCapability(
                method=ScraperMethod.PROXY_CHAIN,
                supports_javascript=True,
                supports_apis=True,
                supports_mobile=True,
                stealth_level=9,
                speed_rating=3,
                resource_usage=8
            ),
            ScraperMethod.STEALTH_MODE: ScraperCapability(
                method=ScraperMethod.STEALTH_MODE,
                supports_javascript=True,
                supports_apis=True,
                supports_mobile=True,
                stealth_level=10,
                speed_rating=2,
                resource_usage=10
            )
        }
        
        # Domain-specific rules
        self.domain_rules = {
            'linkedin.com': {
                'difficulty': TargetDifficulty.EXTREME,
                'requires_javascript': True,
                'preferred_method': ScraperMethod.STEALTH_MODE
            },
            'indeed.com': {
                'difficulty': TargetDifficulty.HARD,
                'requires_javascript': True,
                'preferred_method': ScraperMethod.HEADLESS_BROWSER
            },
            'naukri.com': {
                'difficulty': TargetDifficulty.HARD,
                'requires_javascript': True,
                'preferred_method': ScraperMethod.HEADLESS_BROWSER
            },
            'techcrunch.com': {
                'difficulty': TargetDifficulty.MEDIUM,
                'requires_javascript': True,
                'preferred_method': ScraperMethod.HEADLESS_BROWSER
            },
            'ycombinator.com': {
                'difficulty': TargetDifficulty.MEDIUM,
                'requires_javascript': False,
                'preferred_method': ScraperMethod.REQUESTS_DIRECT
            }
        }
    
    def analyze_target(self, url: str, force_refresh: bool = False) -> TargetAnalysis:
        """
        Analyze a target URL and determine optimal scraping strategy
        
        Args:
            url: Target URL to analyze
            force_refresh: Force re-analysis even if cached
            
        Returns:
            TargetAnalysis with recommendations
        """
        domain = self._extract_domain(url)
        
        # Check cache
        cache_key = f"{domain}_{url}"
        if not force_refresh and cache_key in self.target_cache:
            cached = self.target_cache[cache_key]
            if time.time() - cached.get('timestamp', 0) < self.cache_expiry:
                return cached
        
        # Perform analysis
        analysis = self._perform_target_analysis(url, domain)
        
        # Cache result
        analysis['timestamp'] = time.time()
        self.target_cache[cache_key] = analysis
        
        logger.info(f"Analyzed target {url}: difficulty={analysis.difficulty.value}, method={analysis.recommended_method.value}")
        return analysis
    
    def _perform_target_analysis(self, url: str, domain: str) -> TargetAnalysis:
        """Perform detailed analysis of target"""
        
        # Start with domain-specific rules
        if domain in self.domain_rules:
            rules = self.domain_rules[domain]
            difficulty = rules['difficulty']
            requires_js = rules['requires_javascript']
            preferred_method = rules['preferred_method']
        else:
            # Dynamic analysis
            difficulty = self._detect_difficulty(url, domain)
            requires_js = self._detect_javascript_requirement(url, domain)
            preferred_method = self._determine_preferred_method(difficulty, requires_js)
        
        # Additional detections
        has_api = self._detect_api_endpoints(domain)
        uses_cloudflare = self._detect_cloudflare(domain)
        rate_limit = self._detect_rate_limiting(domain)
        content_type = self._detect_content_type(domain)
        
        # Calculate estimated success rate
        success_rate = self._calculate_success_rate(
            difficulty, requires_js, has_api, uses_cloudflare, rate_limit
        )
        
        # Determine fallback methods
        fallback_methods = self._get_fallback_methods(preferred_method, difficulty)
        
        analysis = TargetAnalysis(
            url=url,
            domain=domain,
            difficulty=difficulty,
            requires_javascript=requires_js,
            has_api_endpoints=has_api,
            uses_cloudflare=uses_cloudflare,
            rate_limit_detected=rate_limit,
            content_type=content_type,
            estimated_success_rate=success_rate,
            recommended_method=preferred_method,
            fallback_methods=fallback_methods
        )
        
        return analysis
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def _detect_difficulty(self, url: str, domain: str) -> TargetDifficulty:
        """Detect target difficulty level"""
        
        # High-difficulty indicators
        high_difficulty_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'tiktok.com', 'pinterest.com', 'snapchat.com', 'reddit.com'
        ]
        
        if domain in high_difficulty_domains:
            return TargetDifficulty.EXTREME
        
        # Medium-difficulty indicators
        medium_difficulty_indicators = [
            'cloudflare', 'akamai', 'fastly', 'imperva', 'distil'
        ]
        
        for indicator in medium_difficulty_indicators:
            if indicator in domain.lower():
                return TargetDifficulty.HARD
        
        # Check for job boards
        job_boards = ['indeed', 'naukri', 'monster', 'dice', 'glassdoor']
        if any(board in domain for board in job_boards):
            return TargetDifficulty.HARD
        
        # Default to medium
        return TargetDifficulty.MEDIUM
    
    def _detect_javascript_requirement(self, url: str, domain: str) -> bool:
        """Detect if target requires JavaScript"""
        
        # Domains known to require JS
        js_required = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'indeed.com', 'naukri.com', 'glassdoor.com', 'angel.co',
            'techcrunch.com', 'businessinsider.com', 'bloomberg.com'
        ]
        
        if domain in js_required:
            return True
        
        # Check for SPA indicators in URL
        spa_indicators = ['/app/', '/dashboard/', '/admin/', '#/']
        if any(indicator in url for indicator in spa_indicators):
            return True
        
        return False
    
    def _determine_preferred_method(self, difficulty: TargetDifficulty, requires_js: bool) -> ScraperMethod:
        """Determine preferred scraping method"""
        
        if difficulty == TargetDifficulty.EXTREME:
            return ScraperMethod.STEALTH_MODE
        elif difficulty == TargetDifficulty.HARD:
            return ScraperMethod.PROXY_CHAIN if requires_js else ScraperMethod.HEADLESS_BROWSER
        elif difficulty == TargetDifficulty.MEDIUM:
            return ScraperMethod.HEADLESS_BROWSER if requires_js else ScraperMethod.REQUESTS_DIRECT
        else:  # EASY
            return ScraperMethod.REQUESTS_DIRECT
    
    def _detect_api_endpoints(self, domain: str) -> bool:
        """Detect if domain has API endpoints"""
        # Common API patterns
        api_domains = ['api.', '.api', 'graphql', 'rest']
        return any(pattern in domain for pattern in api_domains)
    
    def _detect_cloudflare(self, domain: str) -> bool:
        """Detect Cloudflare protection"""
        # This would normally check headers/JS, but for now use known domains
        cloudflare_domains = ['cloudflare.com', 'cdnjs.cloudflare.com']
        return any(cf in domain for cf in cloudflare_domains)
    
    def _detect_rate_limiting(self, domain: str) -> bool:
        """Detect rate limiting"""
        # Known rate-limited domains
        rate_limited = ['linkedin.com', 'twitter.com', 'facebook.com']
        return domain in rate_limited
    
    def _detect_content_type(self, domain: str) -> str:
        """Detect content type (static/dynamic/spa)"""
        spa_domains = ['linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com']
        if domain in spa_domains:
            return 'spa'
        
        dynamic_domains = ['indeed.com', 'naukri.com', 'techcrunch.com']
        if domain in dynamic_domains:
            return 'dynamic'
        
        return 'static'
    
    def _calculate_success_rate(self, difficulty: TargetDifficulty, requires_js: bool,
                              has_api: bool, uses_cloudflare: bool, rate_limit: bool) -> float:
        """Calculate estimated success rate"""
        base_rate = 0.8
        
        # Difficulty modifiers
        if difficulty == TargetDifficulty.EASY:
            base_rate += 0.15
        elif difficulty == TargetDifficulty.HARD:
            base_rate -= 0.1
        elif difficulty == TargetDifficulty.EXTREME:
            base_rate -= 0.25
        
        # JS requirement
        if requires_js:
            base_rate -= 0.1
        
        # API availability
        if has_api:
            base_rate += 0.1
        
        # Cloudflare protection
        if uses_cloudflare:
            base_rate -= 0.2
        
        # Rate limiting
        if rate_limit:
            base_rate -= 0.15
        
        return max(0.1, min(0.99, base_rate))
    
    def _get_fallback_methods(self, primary_method: ScraperMethod, difficulty: TargetDifficulty) -> List[ScraperMethod]:
        """Get fallback methods for primary method"""
        fallbacks = []
        
        # Always include direct requests as fallback
        if primary_method != ScraperMethod.REQUESTS_DIRECT:
            fallbacks.append(ScraperMethod.REQUESTS_DIRECT)
        
        # Add headless browser for JS sites
        if primary_method != ScraperMethod.HEADLESS_BROWSER:
            fallbacks.append(ScraperMethod.HEADLESS_BROWSER)
        
        # Add stealth mode for difficult targets
        if difficulty in [TargetDifficulty.HARD, TargetDifficulty.EXTREME]:
            if primary_method != ScraperMethod.STEALTH_MODE:
                fallbacks.append(ScraperMethod.STEALTH_MODE)
        
        # Add mobile emulation for variety
        if primary_method != ScraperMethod.MOBILE_EMULATION:
            fallbacks.append(ScraperMethod.MOBILE_EMULATION)
        
        return fallbacks[:3]  # Limit to 3 fallbacks
    
    def select_scraper(self, analysis: TargetAnalysis, available_resources: Dict[str, int]) -> ScraperMethod:
        """
        Select optimal scraper based on analysis and available resources
        
        Args:
            analysis: Target analysis
            available_resources: Available system resources
            
        Returns:
            Selected scraper method
        """
        candidates = [analysis.recommended_method] + analysis.fallback_methods
        
        # Filter by capabilities
        filtered_candidates = []
        for method in candidates:
            capability = self.scraper_capabilities[method]
            
            # Check JavaScript requirement
            if analysis.requires_javascript and not capability.supports_javascript:
                continue
            
            # Check API requirement
            if analysis.has_api_endpoints and not capability.supports_apis:
                continue
            
            # Check resource constraints
            if available_resources.get('cpu', 10) < capability.resource_usage:
                continue
            
            if available_resources.get('memory', 10) < capability.resource_usage:
                continue
            
            filtered_candidates.append((method, capability))
        
        if not filtered_candidates:
            # Fallback to basic method
            return ScraperMethod.REQUESTS_DIRECT
        
        # Score candidates
        scored_candidates = []
        for method, capability in filtered_candidates:
            score = self._score_method(method, capability, analysis)
            scored_candidates.append((method, score))
        
        # Select highest scoring method
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        selected_method = scored_candidates[0][0]
        
        logger.info(f"Selected scraper method: {selected_method.value} for {analysis.url}")
        return selected_method
    
    def _score_method(self, method: ScraperMethod, capability: ScraperCapability, analysis: TargetAnalysis) -> float:
        """Score a scraper method for the given analysis"""
        score = capability.success_rate * 0.4  # Base success rate
        
        # Stealth bonus for difficult targets
        if analysis.difficulty in [TargetDifficulty.HARD, TargetDifficulty.EXTREME]:
            score += capability.stealth_level * 0.1
        
        # Speed bonus for easy targets
        if analysis.difficulty == TargetDifficulty.EASY:
            score += capability.speed_rating * 0.1
        
        # Resource efficiency bonus
        score += (11 - capability.resource_usage) * 0.05  # Lower resource usage is better
        
        # JavaScript compatibility bonus
        if analysis.requires_javascript and capability.supports_javascript:
            score += 0.2
        
        # API compatibility bonus
        if analysis.has_api_endpoints and capability.supports_apis:
            score += 0.1
        
        return score
    
    def get_scraper_config(self, method: ScraperMethod, analysis: TargetAnalysis) -> Dict[str, Any]:
        """
        Get configuration for selected scraper method
        
        Args:
            method: Selected scraper method
            analysis: Target analysis
            
        Returns:
            Configuration dictionary
        """
        base_config = {
            'method': method.value,
            'url': analysis.url,
            'domain': analysis.domain,
            'requires_javascript': analysis.requires_javascript,
            'content_type': analysis.content_type
        }
        
        if method == ScraperMethod.HEADLESS_BROWSER:
            base_config.update({
                'wait_for_selector': self._get_wait_selector(analysis),
                'timeout': 30000,
                'stealth_mode': analysis.difficulty in [TargetDifficulty.HARD, TargetDifficulty.EXTREME]
            })
        
        elif method == ScraperMethod.STEALTH_MODE:
            base_config.update({
                'proxy_required': True,
                'fingerprint_rotation': True,
                'human_behavior': True,
                'wait_for_selector': self._get_wait_selector(analysis),
                'timeout': 45000
            })
        
        elif method == ScraperMethod.MOBILE_EMULATION:
            base_config.update({
                'mobile_user_agent': True,
                'viewport': {'width': 375, 'height': 667},
                'touch_events': True
            })
        
        return base_config
    
    def _get_wait_selector(self, analysis: TargetAnalysis) -> Optional[str]:
        """Get appropriate wait selector for target"""
        selectors = {
            'linkedin.com': '.jobs-search__results-list',
            'indeed.com': '.job_seen_beacon',
            'naukri.com': '.srp-jobtuple-wrapper',
            'techcrunch.com': 'article',
            'ycombinator.com': '.company'
        }
        
        return selectors.get(analysis.domain)

# Global instance
adaptive_scraper = AdaptiveScraper()
