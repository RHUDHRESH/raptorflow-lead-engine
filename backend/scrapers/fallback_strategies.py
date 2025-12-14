"""
Fallback Strategy System with cascading fallback approaches.
Provides multiple backup strategies when primary scraping methods fail.
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable, Type, Union
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of scraping failures"""
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    CAPTCHA = "captcha"
    RATE_LIMIT = "rate_limit"
    JS_ERROR = "js_error"
    PARSE_ERROR = "parse_error"
    CONTENT_MISSING = "content_missing"
    UNKNOWN = "unknown"

class FallbackStrategy(Enum):
    """Available fallback strategies"""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SWITCH_PROXY = "switch_proxy"
    CHANGE_USER_AGENT = "change_user_agent"
    USE_HEADLESS_BROWSER = "use_headless_browser"
    MOBILE_EMULATION = "mobile_emulation"
    API_FALLBACK = "api_fallback"
    CACHE_FALLBACK = "cache_fallback"
    SIMPLIFIED_PARSING = "simplified_parsing"
    ALTERNATE_SELECTORS = "alternate_selectors"

@dataclass
class FailureContext:
    """Context information about a scraping failure"""
    url: str
    method: str
    failure_type: FailureType
    error_message: str
    attempt_number: int
    timestamp: float
    response_code: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    proxy_used: Optional[str] = None
    user_agent_used: Optional[str] = None

@dataclass
class FallbackAction:
    """A specific fallback action to take"""
    strategy: FallbackStrategy
    priority: int  # Lower number = higher priority
    config: Dict[str, Any]
    estimated_success_rate: float
    resource_cost: int  # 1-10 scale

@dataclass
class FallbackPlan:
    """Complete fallback plan for a target"""
    primary_method: str
    fallback_actions: List[FallbackAction]
    max_attempts: int
    timeout_multiplier: float
    circuit_breaker_threshold: int

class FallbackManager:
    """
    Manages fallback strategies and executes them when primary methods fail
    """
    
    def __init__(self):
        self.failure_history: Dict[str, List[FailureContext]] = {}
        self.success_cache: Dict[str, Dict[str, float]] = {}  # method -> success rate
        self.circuit_breakers: Dict[str, Dict[str, int]] = {}  # domain -> method -> failure count
        
        # Strategy success rates (learned/adjustable)
        self.strategy_success_rates = {
            FallbackStrategy.RETRY_WITH_BACKOFF: 0.6,
            FallbackStrategy.SWITCH_PROXY: 0.8,
            FallbackStrategy.CHANGE_USER_AGENT: 0.7,
            FallbackStrategy.USE_HEADLESS_BROWSER: 0.85,
            FallbackStrategy.MOBILE_EMULATION: 0.75,
            FallbackStrategy.API_FALLBACK: 0.9,
            FallbackStrategy.CACHE_FALLBACK: 0.95,
            FallbackStrategy.SIMPLIFIED_PARSING: 0.5,
            FallbackStrategy.ALTERNATE_SELECTORS: 0.6
        }
    
    def create_fallback_plan(self, url: str, primary_method: str, context: Dict[str, Any] = None) -> FallbackPlan:
        """
        Create a fallback plan for a target URL
        
        Args:
            url: Target URL
            primary_method: Primary scraping method
            context: Additional context information
            
        Returns:
            FallbackPlan with strategies
        """
        domain = self._extract_domain(url)
        
        # Analyze failure patterns for this domain
        failure_patterns = self._analyze_failure_patterns(domain, primary_method)
        
        # Generate fallback actions based on patterns
        fallback_actions = self._generate_fallback_actions(
            url, domain, primary_method, failure_patterns, context or {}
        )
        
        # Sort by priority and success rate
        fallback_actions.sort(key=lambda x: (x.priority, -x.estimated_success_rate))
        
        plan = FallbackPlan(
            primary_method=primary_method,
            fallback_actions=fallback_actions,
            max_attempts=min(len(fallback_actions) + 1, 5),  # Primary + up to 4 fallbacks
            timeout_multiplier=self._calculate_timeout_multiplier(failure_patterns),
            circuit_breaker_threshold=self._calculate_circuit_breaker_threshold(domain)
        )
        
        return plan
    
    def _analyze_failure_patterns(self, domain: str, method: str) -> Dict[str, Any]:
        """Analyze failure patterns for domain and method"""
        if domain not in self.failure_history:
            return {}
        
        failures = self.failure_history[domain]
        method_failures = [f for f in failures if f.method == method]
        
        if not method_failures:
            return {}
        
        # Analyze patterns
        patterns = {
            'total_failures': len(method_failures),
            'recent_failures': len([f for f in method_failures if time.time() - f.timestamp < 3600]),  # Last hour
            'common_failure_types': {},
            'avg_response_time': 0,
            'success_rate_trend': 'unknown'
        }
        
        # Count failure types
        for failure in method_failures[-20:]:  # Last 20 failures
            failure_type = failure.failure_type.value
            patterns['common_failure_types'][failure_type] = \
                patterns['common_failure_types'].get(failure_type, 0) + 1
        
        # Determine most common failure
        if patterns['common_failure_types']:
            patterns['most_common_failure'] = max(
                patterns['common_failure_types'].items(),
                key=lambda x: x[1]
            )[0]
        
        return patterns
    
    def _generate_fallback_actions(self, url: str, domain: str, primary_method: str,
                                 failure_patterns: Dict[str, Any], context: Dict[str, Any]) -> List[FallbackAction]:
        """Generate appropriate fallback actions"""
        actions = []
        
        # Common failure type responses
        most_common_failure = failure_patterns.get('most_common_failure')
        
        if most_common_failure == 'blocked':
            actions.extend(self._get_blocked_fallbacks(url, domain))
        elif most_common_failure == 'timeout':
            actions.extend(self._get_timeout_fallbacks(url, domain))
        elif most_common_failure == 'rate_limit':
            actions.extend(self._get_rate_limit_fallbacks(url, domain))
        elif most_common_failure == 'js_error':
            actions.extend(self._get_js_error_fallbacks(url, domain))
        elif most_common_failure == 'captcha':
            actions.extend(self._get_captcha_fallbacks(url, domain))
        else:
            # Generic fallbacks
            actions.extend(self._get_generic_fallbacks(url, domain, primary_method))
        
        # Always add cache fallback as last resort
        actions.append(self._create_fallback_action(
            FallbackStrategy.CACHE_FALLBACK,
            priority=10,
            config={'cache_ttl': 3600}
        ))
        
        return actions
    
    def _get_blocked_fallbacks(self, url: str, domain: str) -> List[FallbackAction]:
        """Fallbacks for blocked requests"""
        return [
            self._create_fallback_action(
                FallbackStrategy.SWITCH_PROXY,
                priority=1,
                config={'proxy_type': 'residential', 'country': None}
            ),
            self._create_fallback_action(
                FallbackStrategy.USE_HEADLESS_BROWSER,
                priority=2,
                config={'stealth_mode': True, 'wait_time': 5000}
            ),
            self._create_fallback_action(
                FallbackStrategy.CHANGE_USER_AGENT,
                priority=3,
                config={'rotate_fingerprint': True}
            ),
            self._create_fallback_action(
                FallbackStrategy.MOBILE_EMULATION,
                priority=4,
                config={'device': 'random'}
            )
        ]
    
    def _get_timeout_fallbacks(self, url: str, domain: str) -> List[FallbackAction]:
        """Fallbacks for timeout errors"""
        return [
            self._create_fallback_action(
                FallbackStrategy.RETRY_WITH_BACKOFF,
                priority=1,
                config={'backoff_multiplier': 2, 'max_delay': 30}
            ),
            self._create_fallback_action(
                FallbackStrategy.SWITCH_PROXY,
                priority=2,
                config={'proxy_type': 'fast', 'timeout': 60}
            ),
            self._create_fallback_action(
                FallbackStrategy.SIMPLIFIED_PARSING,
                priority=3,
                config={'skip_javascript': True}
            )
        ]
    
    def _get_rate_limit_fallbacks(self, url: str, domain: str) -> List[FallbackAction]:
        """Fallbacks for rate limiting"""
        return [
            self._create_fallback_action(
                FallbackStrategy.RETRY_WITH_BACKOFF,
                priority=1,
                config={'backoff_multiplier': 3, 'max_delay': 300}
            ),
            self._create_fallback_action(
                FallbackStrategy.SWITCH_PROXY,
                priority=2,
                config={'proxy_type': 'rotating'}
            ),
            self._create_fallback_action(
                FallbackStrategy.API_FALLBACK,
                priority=3,
                config={'endpoint_detection': True}
            )
        ]
    
    def _get_js_error_fallbacks(self, url: str, domain: str) -> List[FallbackAction]:
        """Fallbacks for JavaScript errors"""
        return [
            self._create_fallback_action(
                FallbackStrategy.USE_HEADLESS_BROWSER,
                priority=1,
                config={'wait_for_load': True, 'timeout': 30000}
            ),
            self._create_fallback_action(
                FallbackStrategy.SIMPLIFIED_PARSING,
                priority=2,
                config={'fallback_selectors': True}
            ),
            self._create_fallback_action(
                FallbackStrategy.ALTERNATE_SELECTORS,
                priority=3,
                config={'selector_patterns': self._get_alternate_selectors(domain)}
            )
        ]
    
    def _get_captcha_fallbacks(self, url: str, domain: str) -> List[FallbackAction]:
        """Fallbacks for CAPTCHA challenges"""
        return [
            self._create_fallback_action(
                FallbackStrategy.SWITCH_PROXY,
                priority=1,
                config={'proxy_type': 'residential', 'captcha_solver': True}
            ),
            self._create_fallback_action(
                FallbackStrategy.MOBILE_EMULATION,
                priority=2,
                config={'device': 'mobile', 'human_behavior': True}
            ),
            self._create_fallback_action(
                FallbackStrategy.STEALTH_MODE,
                priority=3,
                config={'maximum_evasion': True}
            )
        ]
    
    def _get_generic_fallbacks(self, url: str, domain: str, primary_method: str) -> List[FallbackAction]:
        """Generic fallback strategies"""
        actions = [
            self._create_fallback_action(
                FallbackStrategy.RETRY_WITH_BACKOFF,
                priority=1,
                config={'attempts': 2}
            )
        ]
        
        # Add method-specific fallbacks
        if primary_method == 'requests_direct':
            actions.append(self._create_fallback_action(
                FallbackStrategy.USE_HEADLESS_BROWSER,
                priority=2,
                config={}
            ))
        elif primary_method == 'headless_browser':
            actions.append(self._create_fallback_action(
                FallbackStrategy.MOBILE_EMULATION,
                priority=2,
                config={}
            ))
        
        return actions
    
    def _create_fallback_action(self, strategy: FallbackStrategy, priority: int, config: Dict[str, Any]) -> FallbackAction:
        """Create a fallback action with calculated success rate"""
        success_rate = self.strategy_success_rates[strategy]
        
        # Adjust success rate based on config
        if config.get('stealth_mode'):
            success_rate += 0.1
        if config.get('proxy_type') == 'residential':
            success_rate += 0.1
        if config.get('human_behavior'):
            success_rate += 0.05
        
        # Calculate resource cost
        resource_cost = 1
        if strategy == FallbackStrategy.USE_HEADLESS_BROWSER:
            resource_cost = 6
        elif strategy == FallbackStrategy.STEALTH_MODE:
            resource_cost = 8
        elif strategy == FallbackStrategy.SWITCH_PROXY:
            resource_cost = 3
        
        return FallbackAction(
            strategy=strategy,
            priority=priority,
            config=config,
            estimated_success_rate=min(0.99, success_rate),
            resource_cost=resource_cost
        )
    
    def _get_alternate_selectors(self, domain: str) -> List[str]:
        """Get alternate selectors for common domains"""
        selector_map = {
            'linkedin.com': ['[data-job-id]', '.job-card-container', '.jobs-search-result'],
            'indeed.com': ['.job_seen_beacon', '.jobsearch-ResultsList-item', '.tapItem'],
            'naukri.com': ['.srp-jobtuple-wrapper', '.jobTuple', '.tuple-wrapper'],
            'techcrunch.com': ['article', '.post-block', '.article-content']
        }
        
        return selector_map.get(domain, ['div', 'article', '.content', '.main'])
    
    def _calculate_timeout_multiplier(self, failure_patterns: Dict[str, Any]) -> float:
        """Calculate timeout multiplier based on failure patterns"""
        if failure_patterns.get('most_common_failure') == 'timeout':
            return 2.0
        elif failure_patterns.get('recent_failures', 0) > 5:
            return 1.5
        else:
            return 1.0
    
    def _calculate_circuit_breaker_threshold(self, domain: str) -> int:
        """Calculate circuit breaker threshold for domain"""
        if domain in ['linkedin.com', 'facebook.com', 'twitter.com']:
            return 3  # More sensitive for difficult domains
        else:
            return 5
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    async def execute_fallback_plan(self, plan: FallbackPlan, scraper_func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Execute a fallback plan with cascading strategies
        
        Args:
            plan: Fallback plan to execute
            scraper_func: Primary scraper function
            *args, **kwargs: Arguments for scraper function
            
        Returns:
            Scraping result or None if all methods failed
        """
        # Check circuit breaker
        domain = self._extract_domain(kwargs.get('url', args[0] if args else ''))
        if self._is_circuit_breaker_open(domain, plan.primary_method):
            logger.warning(f"Circuit breaker open for {domain}, skipping")
            return None
        
        # Try primary method first
        logger.info(f"Attempting primary method: {plan.primary_method}")
        try:
            result = await scraper_func(*args, **kwargs)
            if result:
                self._record_success(domain, plan.primary_method)
                return result
        except Exception as e:
            failure_context = FailureContext(
                url=kwargs.get('url', args[0] if args else ''),
                method=plan.primary_method,
                failure_type=self._classify_failure(e),
                error_message=str(e),
                attempt_number=1,
                timestamp=time.time()
            )
            self._record_failure(domain, failure_context)
        
        # Try fallback strategies
        for i, action in enumerate(plan.fallback_actions):
            if i + 1 >= plan.max_attempts:
                break
            
            logger.info(f"Attempting fallback {i+1}: {action.strategy.value}")
            
            try:
                # Modify kwargs based on fallback action
                modified_kwargs = self._apply_fallback_config(action, kwargs.copy())
                modified_kwargs['timeout'] = modified_kwargs.get('timeout', 30) * plan.timeout_multiplier
                
                result = await scraper_func(*args, **modified_kwargs)
                if result:
                    self._record_success(domain, action.strategy.value)
                    logger.info(f"Fallback successful: {action.strategy.value}")
                    return result
                    
            except Exception as e:
                failure_context = FailureContext(
                    url=kwargs.get('url', args[0] if args else ''),
                    method=action.strategy.value,
                    failure_type=self._classify_failure(e),
                    error_message=str(e),
                    attempt_number=i + 2,
                    timestamp=time.time()
                )
                self._record_failure(domain, failure_context)
                logger.warning(f"Fallback failed: {action.strategy.value} - {e}")
        
        # All methods failed
        logger.error(f"All fallback strategies failed for {domain}")
        return None
    
    def _apply_fallback_config(self, action: FallbackAction, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fallback configuration to kwargs"""
        config = action.config
        
        if action.strategy == FallbackStrategy.SWITCH_PROXY:
            kwargs['proxy_config'] = config
        elif action.strategy == FallbackStrategy.CHANGE_USER_AGENT:
            kwargs['rotate_user_agent'] = True
        elif action.strategy == FallbackStrategy.USE_HEADLESS_BROWSER:
            kwargs['use_headless'] = True
            kwargs['wait_time'] = config.get('wait_time', 2000)
        elif action.strategy == FallbackStrategy.MOBILE_EMULATION:
            kwargs['mobile_emulation'] = True
            kwargs['device'] = config.get('device', 'random')
        elif action.strategy == FallbackStrategy.API_FALLBACK:
            kwargs['prefer_api'] = True
        elif action.strategy == FallbackStrategy.SIMPLIFIED_PARSING:
            kwargs['simplified_parsing'] = True
        elif action.strategy == FallbackStrategy.ALTERNATE_SELECTORS:
            kwargs['alternate_selectors'] = config.get('selector_patterns', [])
        
        return kwargs
    
    def _classify_failure(self, exception: Exception) -> FailureType:
        """Classify the type of failure from exception"""
        error_msg = str(exception).lower()
        
        if 'timeout' in error_msg or 'timed out' in error_msg:
            return FailureType.TIMEOUT
        elif '403' in error_msg or 'blocked' in error_msg or 'forbidden' in error_msg:
            return FailureType.BLOCKED
        elif 'captcha' in error_msg or 'verification' in error_msg:
            return FailureType.CAPTCHA
        elif '429' in error_msg or 'rate limit' in error_msg:
            return FailureType.RATE_LIMIT
        elif 'javascript' in error_msg or 'js error' in error_msg:
            return FailureType.JS_ERROR
        elif 'parse' in error_msg or 'selector' in error_msg:
            return FailureType.PARSE_ERROR
        elif '404' in error_msg or 'not found' in error_msg:
            return FailureType.CONTENT_MISSING
        elif 'connection' in error_msg or 'network' in error_msg:
            return FailureType.NETWORK_ERROR
        else:
            return FailureType.UNKNOWN
    
    def _record_failure(self, domain: str, failure_context: FailureContext):
        """Record a scraping failure"""
        if domain not in self.failure_history:
            self.failure_history[domain] = []
        
        self.failure_history[domain].append(failure_context)
        
        # Keep only recent failures (last 100)
        if len(self.failure_history[domain]) > 100:
            self.failure_history[domain] = self.failure_history[domain][-100:]
        
        # Update circuit breaker
        method = failure_context.method
        if domain not in self.circuit_breakers:
            self.circuit_breakers[domain] = {}
        if method not in self.circuit_breakers[domain]:
            self.circuit_breakers[domain][method] = 0
        
        self.circuit_breakers[domain][method] += 1
    
    def _record_success(self, domain: str, method: str):
        """Record a successful scrape"""
        # Reset circuit breaker
        if domain in self.circuit_breakers and method in self.circuit_breakers[domain]:
            self.circuit_breakers[domain][method] = 0
        
        # Update success cache
        if domain not in self.success_cache:
            self.success_cache[domain] = {}
        self.success_cache[domain][method] = time.time()
    
    def _is_circuit_breaker_open(self, domain: str, method: str) -> bool:
        """Check if circuit breaker is open for domain/method"""
        if domain not in self.circuit_breakers:
            return False
        
        failure_count = self.circuit_breakers[domain].get(method, 0)
        threshold = self._calculate_circuit_breaker_threshold(domain)
        
        return failure_count >= threshold

# Global instance
fallback_manager = FallbackManager()
