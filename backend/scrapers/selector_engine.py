"""
Adaptive Selector Engine with machine learning-based element identification.
Provides self-healing selectors that adapt to site changes and multiple selector strategies.
"""
import logging
import time
import re
import hashlib
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse
from collections import defaultdict, Counter
import json

logger = logging.getLogger(__name__)

class SelectorType(Enum):
    """Types of selectors available"""
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ATTRIBUTE = "attribute"
    POSITIONAL = "positional"
    SEMANTIC = "semantic"

class SelectorPriority(Enum):
    """Selector priority levels"""
    PRIMARY = "primary"
    BACKUP = "backup"
    FALLBACK = "fallback"
    EXPERIMENTAL = "experimental"

@dataclass
class SelectorCandidate:
    """A candidate selector with metadata"""
    selector: str
    selector_type: SelectorType
    priority: SelectorPriority
    success_rate: float
    last_success: Optional[float]
    last_failure: Optional[float]
    usage_count: int
    element_count: int  # Expected number of elements to match
    context_hints: List[str]  # Additional context for matching

@dataclass
class ElementSignature:
    """Signature of an HTML element for identification"""
    tag_name: str
    attributes: Dict[str, str]
    text_content: Optional[str]
    position: Optional[Tuple[int, int]]  # Relative position
    parent_signature: Optional[str]  # Hash of parent element
    sibling_count: int
    child_count: int

@dataclass
class SelectorResult:
    """Result of selector application"""
    selector: str
    elements_found: int
    success: bool
    execution_time: float
    error_message: Optional[str]

class AdaptiveSelectorEngine:
    """
    Machine learning-based selector engine that adapts to site changes
    """
    
    def __init__(self):
        self.selector_cache: Dict[str, List[SelectorCandidate]] = {}
        self.element_signatures: Dict[str, ElementSignature] = {}
        self.selector_performance: Dict[str, Dict[str, float]] = {}
        
        # Domain-specific selector patterns
        self.domain_patterns = self._initialize_domain_patterns()
        
        # Learning data
        self.learning_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.selector_evolution: Dict[str, List[str]] = defaultdict(list)
    
    def _initialize_domain_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize domain-specific selector patterns"""
        return {
            'linkedin.com': {
                'job_cards': [
                    '.jobs-search__results-list li',
                    '.job-card-container',
                    '[data-job-id]',
                    '.jobs-search-result-item'
                ],
                'job_titles': [
                    'h3.base-search-card__title a',
                    '.job-card-list__title',
                    '[data-tracking-control-name="public_jobs_jserp-result_search-card"] h3'
                ],
                'company_names': [
                    'h4.base-search-card__subtitle a',
                    '.job-card-container__company-name',
                    '.job-card-container__primary-description'
                ]
            },
            'indeed.com': {
                'job_cards': [
                    '.job_seen_beacon',
                    '.tapItem',
                    '.jobsearch-ResultsList-item',
                    '[data-jk]'
                ],
                'job_titles': [
                    'h2.jobTitle a',
                    '.jobTitle a',
                    'td.resultContent h2 a'
                ],
                'company_names': [
                    'span.companyName',
                    '[data-testid="company-name"]',
                    '.companyName'
                ]
            },
            'naukri.com': {
                'job_cards': [
                    '.srp-jobtuple-wrapper',
                    '.jobTuple',
                    '.tuple-wrapper'
                ],
                'job_titles': [
                    'a.title',
                    '.jobtitle a',
                    '.desig'
                ],
                'company_names': [
                    'a.comp-name',
                    '.comp-name',
                    'span.comp-name'
                ]
            },
            'techcrunch.com': {
                'article_cards': [
                    'article',
                    '.post-block',
                    '.article-content',
                    '.river-block'
                ],
                'article_titles': [
                    'h2 a',
                    '.post-block__title a',
                    '.article-title a'
                ],
                'article_dates': [
                    'time',
                    '.river-byline__date',
                    '.post-block__metadata time'
                ]
            }
        }
    
    def find_selectors(self, domain: str, element_type: str, html_content: str,
                      target_text: Optional[str] = None) -> List[SelectorCandidate]:
        """
        Find optimal selectors for an element type on a domain
        
        Args:
            domain: Website domain
            element_type: Type of element (job_cards, job_titles, etc.)
            html_content: HTML content to analyze
            target_text: Optional target text to match
            
        Returns:
            List of selector candidates
        """
        cache_key = f"{domain}_{element_type}"
        
        # Check cache first
        if cache_key in self.selector_cache:
            cached_selectors = self.selector_cache[cache_key]
            # Filter out low-performing selectors
            active_selectors = [s for s in cached_selectors if s.success_rate > 0.5]
            if active_selectors:
                return active_selectors
        
        # Generate new selectors
        candidates = self._generate_selectors(domain, element_type, html_content, target_text)
        
        # Rank and filter selectors
        ranked_candidates = self._rank_selectors(candidates, html_content)
        
        # Cache results
        self.selector_cache[cache_key] = ranked_candidates
        
        logger.info(f"Generated {len(ranked_candidates)} selectors for {domain}.{element_type}")
        return ranked_candidates
    
    def _generate_selectors(self, domain: str, element_type: str, html_content: str,
                           target_text: Optional[str] = None) -> List[SelectorCandidate]:
        """Generate potential selectors for an element type"""
        candidates = []
        
        # Start with domain-specific patterns
        if domain in self.domain_patterns and element_type in self.domain_patterns[domain]:
            for selector in self.domain_patterns[domain][element_type]:
                candidate = SelectorCandidate(
                    selector=selector,
                    selector_type=self._classify_selector_type(selector),
                    priority=SelectorPriority.PRIMARY,
                    success_rate=0.8,  # Assume good for known patterns
                    last_success=time.time(),
                    last_failure=None,
                    usage_count=0,
                    element_count=0,
                    context_hints=[f"domain_{domain}", f"type_{element_type}"]
                )
                candidates.append(candidate)
        
        # Generate dynamic selectors based on HTML analysis
        dynamic_selectors = self._analyze_html_for_selectors(html_content, element_type, target_text)
        candidates.extend(dynamic_selectors)
        
        # Generate semantic selectors
        semantic_selectors = self._generate_semantic_selectors(html_content, element_type, target_text)
        candidates.extend(semantic_selectors)
        
        # Generate fallback selectors
        fallback_selectors = self._generate_fallback_selectors(element_type)
        candidates.extend(fallback_selectors)
        
        return candidates
    
    def _classify_selector_type(self, selector: str) -> SelectorType:
        """Classify the type of a selector"""
        if selector.startswith('//') or selector.startswith('.//'):
            return SelectorType.XPATH
        elif selector.startswith('[') and ']' in selector:
            return SelectorType.ATTRIBUTE
        elif any(char in selector for char in ['>', '+', '~', ' ']):
            return SelectorType.CSS
        elif selector in ['h1', 'h2', 'h3', 'div', 'span', 'a', 'p']:
            return SelectorType.SEMANTIC
        else:
            return SelectorType.CSS
    
    def _analyze_html_for_selectors(self, html_content: str, element_type: str,
                                   target_text: Optional[str] = None) -> List[SelectorCandidate]:
        """Analyze HTML to generate dynamic selectors"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml')
        candidates = []
        
        # Common patterns for different element types
        patterns = {
            'job_cards': {
                'tags': ['div', 'li', 'article'],
                'classes': ['job', 'card', 'item', 'result', 'posting'],
                'attributes': ['data-job', 'data-jk', 'data-id']
            },
            'job_titles': {
                'tags': ['h1', 'h2', 'h3', 'a'],
                'classes': ['title', 'jobtitle', 'position'],
                'attributes': ['title', 'data-jobtitle']
            },
            'company_names': {
                'tags': ['span', 'div', 'a'],
                'classes': ['company', 'employer', 'org'],
                'attributes': ['data-company']
            },
            'article_cards': {
                'tags': ['article', 'div'],
                'classes': ['post', 'article', 'entry', 'card'],
                'attributes': ['data-post-id']
            }
        }
        
        if element_type not in patterns:
            return candidates
        
        pattern = patterns[element_type]
        
        # Find elements by class patterns
        for class_pattern in pattern['classes']:
            elements = soup.find_all(attrs={'class': re.compile(class_pattern, re.I)})
            for element in elements[:5]:  # Limit to avoid noise
                selector = self._generate_selector_for_element(element)
                if selector:
                    candidate = SelectorCandidate(
                        selector=selector,
                        selector_type=SelectorType.CSS,
                        priority=SelectorPriority.BACKUP,
                        success_rate=0.6,
                        last_success=None,
                        last_failure=None,
                        usage_count=0,
                        element_count=1,
                        context_hints=[f"dynamic_{element_type}"]
                    )
                    candidates.append(candidate)
        
        # Find elements by attribute patterns
        for attr_pattern in pattern['attributes']:
            elements = soup.find_all(attrs={attr_pattern: True})
            for element in elements[:3]:
                selector = f"[{attr_pattern}]"
                candidate = SelectorCandidate(
                    selector=selector,
                    selector_type=SelectorType.ATTRIBUTE,
                    priority=SelectorPriority.BACKUP,
                    success_rate=0.7,
                    last_success=None,
                    last_failure=None,
                    usage_count=0,
                    element_count=len(elements),
                    context_hints=[f"attr_{attr_pattern}"]
                )
                candidates.append(candidate)
        
        return candidates
    
    def _generate_semantic_selectors(self, html_content: str, element_type: str,
                                    target_text: Optional[str] = None) -> List[SelectorCandidate]:
        """Generate semantic selectors based on content analysis"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml')
        candidates = []
        
        # Semantic patterns for different content types
        semantic_patterns = {
            'job_titles': [
                {'tag': 'h1', 'context': 'job'},
                {'tag': 'h2', 'context': 'job'},
                {'tag': 'h3', 'context': 'job'},
                {'tag': 'a', 'contains': ['job', 'position', 'role']}
            ],
            'company_names': [
                {'tag': 'span', 'class': 'company'},
                {'tag': 'div', 'class': 'company'},
                {'tag': 'a', 'href': 'company'}
            ],
            'article_titles': [
                {'tag': 'h1', 'context': 'article'},
                {'tag': 'h2', 'context': 'article'},
                {'tag': 'a', 'class': 'title'}
            ]
        }
        
        if element_type not in semantic_patterns:
            return candidates
        
        for pattern in semantic_patterns[element_type]:
            elements = soup.find_all(**{k: v for k, v in pattern.items() if k != 'context'})
            
            for element in elements[:3]:
                selector = self._generate_semantic_selector(element, pattern)
                if selector:
                    candidate = SelectorCandidate(
                        selector=selector,
                        selector_type=SelectorType.SEMANTIC,
                        priority=SelectorPriority.EXPERIMENTAL,
                        success_rate=0.4,
                        last_success=None,
                        last_failure=None,
                        usage_count=0,
                        element_count=1,
                        context_hints=[f"semantic_{element_type}"]
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _generate_fallback_selectors(self, element_type: str) -> List[SelectorCandidate]:
        """Generate fallback selectors as last resort"""
        fallbacks = []
        
        # Generic fallbacks based on element type
        fallback_patterns = {
            'job_cards': ['div', 'li', 'article', '.card', '.item'],
            'job_titles': ['h1', 'h2', 'h3', 'a', '.title'],
            'company_names': ['span', 'div', 'a', '.company'],
            'article_cards': ['article', 'div', '.post', '.entry']
        }
        
        if element_type in fallback_patterns:
            for selector in fallback_patterns[element_type]:
                candidate = SelectorCandidate(
                    selector=selector,
                    selector_type=SelectorType.CSS,
                    priority=SelectorPriority.FALLBACK,
                    success_rate=0.2,
                    last_success=None,
                    last_failure=None,
                    usage_count=0,
                    element_count=0,
                    context_hints=[f"fallback_{element_type}"]
                )
                fallbacks.append(candidate)
        
        return fallbacks
    
    def _generate_selector_for_element(self, element) -> Optional[str]:
        """Generate a CSS selector for a BeautifulSoup element"""
        try:
            # Try ID first (most specific)
            if element.get('id'):
                return f"#{element['id']}"
            
            # Try classes
            classes = element.get('class', [])
            if classes:
                # Use first class
                return f".{classes[0]}"
            
            # Try data attributes
            for attr, value in element.attrs.items():
                if attr.startswith('data-'):
                    return f"[{attr}]"
            
            # Fallback to tag name
            return element.name
            
        except Exception:
            return None
    
    def _generate_semantic_selector(self, element, pattern: Dict[str, Any]) -> Optional[str]:
        """Generate a semantic selector"""
        try:
            base_selector = element.name
            
            # Add class if present
            if 'class' in pattern and element.get('class'):
                base_selector += f".{element['class'][0]}"
            
            # Add attribute conditions
            for attr, value in pattern.items():
                if attr not in ['tag', 'context'] and element.get(attr):
                    if isinstance(value, str):
                        base_selector += f"[{attr}*='{value}']"
                    elif isinstance(value, list):
                        for val in value:
                            if val in str(element.get(attr, '')):
                                base_selector += f"[{attr}*='{val}']"
                                break
            
            return base_selector
            
        except Exception:
            return None
    
    def _rank_selectors(self, candidates: List[SelectorCandidate], html_content: str) -> List[SelectorCandidate]:
        """Rank selectors by expected performance"""
        
        # Test each selector against the HTML
        tested_candidates = []
        for candidate in candidates:
            result = self._test_selector(candidate.selector, html_content)
            
            # Update candidate based on test results
            candidate.element_count = result.elements_found
            candidate.success_rate = min(1.0, candidate.success_rate * (1.0 if result.success else 0.8))
            
            if result.success:
                candidate.last_success = time.time()
                candidate.usage_count += 1
            else:
                candidate.last_failure = time.time()
            
            tested_candidates.append(candidate)
        
        # Rank by multiple factors
        tested_candidates.sort(key=lambda x: (
            -x.success_rate,  # Higher success rate first
            -x.usage_count,   # More used selectors first
            x.priority.value == SelectorPriority.PRIMARY,  # Primary priority first
            -x.element_count  # More specific selectors first (fewer matches)
        ), reverse=True)
        
        # Return top selectors
        return tested_candidates[:10]
    
    def _test_selector(self, selector: str, html_content: str) -> SelectorResult:
        """Test a selector against HTML content"""
        start_time = time.time()
        error_message = None
        
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'lxml')
            
            if selector.startswith('//'):
                # XPath selector (limited support with BeautifulSoup)
                # For now, treat as CSS
                selector = selector.replace('//', '').replace('[@', '[')
            
            elements = soup.select(selector)
            elements_found = len(elements)
            
            # Basic validation
            success = elements_found > 0
            
            execution_time = time.time() - start_time
            return SelectorResult(selector, elements_found, success, execution_time, None)
            
        except Exception as e:
            execution_time = time.time() - start_time
            return SelectorResult(selector, 0, False, execution_time, str(e))
    
    def adapt_selectors(self, domain: str, element_type: str, failed_selectors: List[str],
                       successful_selectors: List[str], html_content: str):
        """
        Adapt selectors based on success/failure feedback
        
        Args:
            domain: Website domain
            element_type: Type of element
            failed_selectors: Selectors that failed
            successful_selectors: Selectors that succeeded
            html_content: Current HTML content for analysis
        """
        cache_key = f"{domain}_{element_type}"
        
        if cache_key not in self.selector_cache:
            return
        
        candidates = self.selector_cache[cache_key]
        
        # Update performance metrics
        for candidate in candidates:
            if candidate.selector in successful_selectors:
                candidate.success_rate = min(1.0, candidate.success_rate + 0.1)
                candidate.last_success = time.time()
                candidate.usage_count += 1
            elif candidate.selector in failed_selectors:
                candidate.success_rate = max(0.0, candidate.success_rate - 0.2)
                candidate.last_failure = time.time()
        
        # Generate new selectors if many are failing
        failing_selectors = [c for c in candidates if c.success_rate < 0.3]
        if len(failing_selectors) > len(candidates) * 0.5:
            logger.info(f"High failure rate for {cache_key}, generating new selectors")
            new_selectors = self._analyze_html_for_selectors(html_content, element_type)
            candidates.extend(new_selectors)
            
            # Re-rank
            candidates = self._rank_selectors(candidates, html_content)
            self.selector_cache[cache_key] = candidates
        
        # Record learning data
        learning_record = {
            'timestamp': time.time(),
            'failed_selectors': failed_selectors,
            'successful_selectors': successful_selectors,
            'html_hash': hashlib.md5(html_content.encode()).hexdigest()[:8]
        }
        self.learning_data[cache_key].append(learning_record)
        
        # Keep only recent learning data
        if len(self.learning_data[cache_key]) > 100:
            self.learning_data[cache_key] = self.learning_data[cache_key][-100:]
    
    def get_optimal_selector(self, domain: str, element_type: str, html_content: str,
                           target_text: Optional[str] = None) -> Optional[SelectorCandidate]:
        """
        Get the optimal selector for an element type
        
        Args:
            domain: Website domain
            element_type: Type of element
            html_content: HTML content
            target_text: Optional target text
            
        Returns:
            Best selector candidate or None
        """
        candidates = self.find_selectors(domain, element_type, html_content, target_text)
        
        if not candidates:
            return None
        
        # Return the highest-ranked candidate
        return candidates[0]
    
    def get_selector_chain(self, domain: str, element_type: str, html_content: str,
                          max_selectors: int = 3) -> List[SelectorCandidate]:
        """
        Get a chain of selectors to try (fallback chain)
        
        Args:
            domain: Website domain
            element_type: Type of element
            html_content: HTML content
            max_selectors: Maximum number of selectors to return
            
        Returns:
            List of selector candidates to try in order
        """
        candidates = self.find_selectors(domain, element_type, html_content)
        
        # Return top N candidates
        return candidates[:max_selectors]

# Global instance
selector_engine = AdaptiveSelectorEngine()
