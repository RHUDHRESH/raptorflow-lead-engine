"""
Pattern Recognition System with NLP for job description pattern matching.
Provides company information extraction templates and validation algorithms.
"""
import logging
import re
import time
from typing import Dict, Any, Optional, List, Set, Tuple, Pattern
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ContentType(Enum):
    """Types of content that can be analyzed"""
    JOB_DESCRIPTION = "job_description"
    COMPANY_PROFILE = "company_profile"
    CONTACT_INFO = "contact_info"
    PRESS_RELEASE = "press_release"
    SOCIAL_POST = "social_post"
    WEBSITE_CONTENT = "website_content"

class PatternCategory(Enum):
    """Categories of patterns"""
    HIRING_SIGNALS = "hiring_signals"
    COMPANY_INFO = "company_info"
    CONTACT_DETAILS = "contact_details"
    JOB_REQUIREMENTS = "job_requirements"
    COMPANY_SIZE = "company_size"
    INDUSTRY_SIGNALS = "industry_signals"

@dataclass
class PatternMatch:
    """Result of pattern matching"""
    pattern_name: str
    matched_text: str
    confidence: float
    start_position: int
    end_position: int
    context: str
    category: PatternCategory
    extracted_data: Dict[str, Any]

@dataclass
class ExtractionTemplate:
    """Template for extracting structured data"""
    name: str
    content_type: ContentType
    patterns: List[Pattern[str]]
    extraction_rules: Dict[str, Any]
    validation_rules: Dict[str, Any]
    confidence_threshold: float

@dataclass
class ValidationResult:
    """Result of data validation"""
    field_name: str
    value: Any
    is_valid: bool
    confidence: float
    validation_errors: List[str]

class PatternMatcher:
    """
    NLP-based pattern recognition for lead generation content
    """
    
    def __init__(self):
        self.patterns: Dict[str, List[Pattern[str]]] = {}
        self.extraction_templates: Dict[str, ExtractionTemplate] = {}
        self.validation_cache: Dict[str, ValidationResult] = {}
        
        # Initialize patterns
        self._initialize_patterns()
        self._initialize_extraction_templates()
    
    def _initialize_patterns(self):
        """Initialize regex patterns for different content types"""
        
        # Hiring signal patterns
        self.patterns['hiring_signals'] = [
            re.compile(r'(?i)(?:we\'re|we are|we\'re currently|currently)\s+(?:hiring|recruiting|looking for|seeking|expanding|growing)', re.MULTILINE),
            re.compile(r'(?i)(?:join our|join the)\s+(?:team|company|growing team)', re.MULTILINE),
            re.compile(r'(?i)(?:open positions?|job openings?|careers? opportunities?)', re.MULTILINE),
            re.compile(r'(?i)(?:we\'re looking to|we are looking to)\s+(?:add|hire|bring on)', re.MULTILINE),
            re.compile(r'(?i)(?:exciting opportunity|great opportunity)\s+(?:to join|at our company)', re.MULTILINE),
            re.compile(r'(?i)(?:work with us|come work with us|join us)', re.MULTILINE),
            re.compile(r'(?i)(?:building (?:our|the) team|scaling (?:our|the) team)', re.MULTILINE),
            re.compile(r'(?i)(?:hiring for|recruiting for)\s+(?:multiple|several|new)', re.MULTILINE)
        ]
        
        # Job title patterns
        self.patterns['job_titles'] = [
            re.compile(r'(?i)\b(marketing|sales|growth|product|engineering|developer|designer)\s+(?:manager|director|lead|head|specialist|coordinator)\b'),
            re.compile(r'(?i)\b(senior|junior|lead|principal|staff)\s+(?:software|frontend|backend|full.?stack|mobile)\s+engineer\b'),
            re.compile(r'(?i)\b(growth|marketing|sales|revenue|business)\s+(?:analyst|associate|representative|specialist)\b'),
            re.compile(r'(?i)\b(content|social media|digital marketing|seo|sem|ppc)\s+(?:manager|specialist|coordinator)\b'),
            re.compile(r'(?i)\b(product|program|project)\s+(?:manager|owner|lead)\b'),
            re.compile(r'(?i)\b(data|business intelligence|analytics)\s+(?:analyst|scientist|engineer)\b')
        ]
        
        # Company size patterns
        self.patterns['company_size'] = [
            re.compile(r'(?i)\b(\d+)(?:\+|\s*-\s*\d+)?\s+(?:employees?|people|team members?|staff)\b'),
            re.compile(r'(?i)\b(team of|company of)\s+(\d+)(?:\+|\s*-\s*\d+)?\b'),
            re.compile(r'(?i)\b(startup|small business|mid.?size|enterprise|large corporation)\b'),
            re.compile(r'(?i)\b(bootstrapped|funded|series [a-z]|pre.?seed|seed|series a|b|c)\b'),
            re.compile(r'(?i)\b(\d+(?:\.\d+)?)\s+(?:million|billion|m|b)\s+(?:in|of)\s+(?:revenue|funding|valuation)\b')
        ]
        
        # Contact information patterns
        self.patterns['contact_info'] = [
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            re.compile(r'\b(?:\+91|91)?[-.\s]?([6-9][0-9]{9})\b'),  # Indian mobile
            re.compile(r'(?i)\b(?:linkedin|twitter|facebook|instagram)\.com/[a-zA-Z0-9_-]+\b')
        ]
        
        # Industry signals
        self.patterns['industry_signals'] = [
            re.compile(r'(?i)\b(?:saas|software as a service|ecommerce|d2c|direct to consumer|fintech|healthtech|edtech)\b'),
            re.compile(r'(?i)\b(?:b2b|b2c|marketplace|platform|api.?first|mobile.?first)\b'),
            re.compile(r'(?i)\b(?:subscription|freemium|freemium model|saas metrics|monthly recurring revenue|mrr|arr)\b'),
            re.compile(r'(?i)\b(?:growth hacking|viral marketing|product.?market fit|scalability)\b'),
            re.compile(r'(?i)\b(?:remote.?first|distributed team|async communication|flexible hours)\b')
        ]
    
    def _initialize_extraction_templates(self):
        """Initialize extraction templates for structured data"""
        
        # Job posting template
        job_template = ExtractionTemplate(
            name="job_posting",
            content_type=ContentType.JOB_DESCRIPTION,
            patterns=[
                re.compile(r'(?i)(?:job title|position|role):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:company|organization):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:location|place|city):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:salary|compensation|pay):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:experience|years? required?):\s*([^\n\r]+)', re.MULTILINE)
            ],
            extraction_rules={
                'job_title': {'pattern': 0, 'required': True, 'validation': 'not_empty'},
                'company': {'pattern': 1, 'required': True, 'validation': 'not_empty'},
                'location': {'pattern': 2, 'required': False, 'validation': 'location_format'},
                'salary': {'pattern': 3, 'required': False, 'validation': 'salary_format'},
                'experience': {'pattern': 4, 'required': False, 'validation': 'experience_format'}
            },
            validation_rules={
                'not_empty': lambda x: bool(x and x.strip()),
                'location_format': lambda x: bool(re.match(r'(?i)(?:remote|hybrid|on.?site|[a-z\s,]+(?:\b(?:india|usa|us|uk|canada|europe|asia)\b)?)', x.strip())),
                'salary_format': lambda x: bool(re.search(r'(?i)(\$|₹|€|£|\b(?:lakh|lpa|k|thousand)\b|\d)', x)),
                'experience_format': lambda x: bool(re.search(r'(?i)(\d+\+?\s*years?|entry|mid|senior|junior)', x))
            },
            confidence_threshold=0.7
        )
        
        # Company profile template
        company_template = ExtractionTemplate(
            name="company_profile",
            content_type=ContentType.COMPANY_PROFILE,
            patterns=[
                re.compile(r'(?i)(?:company|organization|about):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:industry|sector|field):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:size|employees|team size):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:founded|established|started):\s*([^\n\r]+)', re.MULTILINE),
                re.compile(r'(?i)(?:website|url|domain):\s*([^\n\r]+)', re.MULTILINE)
            ],
            extraction_rules={
                'company_name': {'pattern': 0, 'required': True, 'validation': 'not_empty'},
                'industry': {'pattern': 1, 'required': False, 'validation': 'industry_check'},
                'company_size': {'pattern': 2, 'required': False, 'validation': 'size_format'},
                'founded_year': {'pattern': 3, 'required': False, 'validation': 'year_format'},
                'website': {'pattern': 4, 'required': False, 'validation': 'url_format'}
            },
            validation_rules={
                'not_empty': lambda x: bool(x and x.strip()),
                'industry_check': lambda x: bool(x.strip() and len(x.split()) <= 5),  # Reasonable industry name length
                'size_format': lambda x: bool(re.search(r'(?i)(\d+|\b(?:small|medium|large|startup|enterprise)\b)', x)),
                'year_format': lambda x: bool(re.search(r'\b(19|20)\d{2}\b', x)),
                'url_format': lambda x: bool(re.match(r'https?://[^\s]+', x.strip()))
            },
            confidence_threshold=0.6
        )
        
        # Contact info template
        contact_template = ExtractionTemplate(
            name="contact_info",
            content_type=ContentType.CONTACT_INFO,
            patterns=[
                re.compile(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'),
                re.compile(r'\b(\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4}))\b'),
                re.compile(r'\b((\+91|91)?[-.\s]?([6-9][0-9]{9}))\b'),
                re.compile(r'(?i)\b((?:linkedin|twitter|facebook|instagram)\.com/[a-zA-Z0-9_-]+)\b')
            ],
            extraction_rules={
                'emails': {'pattern': 0, 'required': False, 'validation': 'email_format', 'multiple': True},
                'phones': {'pattern': [1, 2], 'required': False, 'validation': 'phone_format', 'multiple': True},
                'social_links': {'pattern': 3, 'required': False, 'validation': 'social_format', 'multiple': True}
            },
            validation_rules={
                'email_format': lambda x: bool(re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', x)),
                'phone_format': lambda x: bool(re.search(r'\d{10,}', re.sub(r'[^\d]', '', x))),
                'social_format': lambda x: bool(re.match(r'(?:linkedin|twitter|facebook|instagram)\.com/[a-zA-Z0-9_-]+', x, re.I))
            },
            confidence_threshold=0.8
        )
        
        self.extraction_templates = {
            'job_posting': job_template,
            'company_profile': company_template,
            'contact_info': contact_template
        }
    
    def analyze_content(self, content: str, content_type: ContentType) -> Dict[str, Any]:
        """
        Analyze content and extract structured information
        
        Args:
            content: Text content to analyze
            content_type: Type of content being analyzed
            
        Returns:
            Dictionary with extracted information and analysis
        """
        analysis = {
            'content_type': content_type.value,
            'content_length': len(content),
            'patterns_found': [],
            'extracted_data': {},
            'confidence_score': 0.0,
            'validation_results': []
        }
        
        # Find all pattern matches
        all_matches = []
        
        for category_name, patterns in self.patterns.items():
            category = PatternCategory(category_name)
            for pattern in patterns:
                matches = pattern.finditer(content)
                for match in matches:
                    pattern_match = PatternMatch(
                        pattern_name=f"{category_name}_{patterns.index(pattern)}",
                        matched_text=match.group(0),
                        confidence=self._calculate_match_confidence(match, content),
                        start_position=match.start(),
                        end_position=match.end(),
                        context=self._extract_context(content, match.start(), match.end()),
                        category=category,
                        extracted_data=self._extract_pattern_data(match, category)
                    )
                    all_matches.append(pattern_match)
        
        analysis['patterns_found'] = [self._pattern_match_to_dict(m) for m in all_matches]
        
        # Extract structured data using templates
        template_name = self._get_template_for_content_type(content_type)
        if template_name and template_name in self.extraction_templates:
            template = self.extraction_templates[template_name]
            extracted_data, validation_results = self._extract_with_template(content, template)
            analysis['extracted_data'] = extracted_data
            analysis['validation_results'] = [self._validation_to_dict(v) for v in validation_results]
            analysis['confidence_score'] = self._calculate_extraction_confidence(validation_results)
        
        # Add category-specific analysis
        analysis.update(self._analyze_content_categories(content, all_matches))
        
        return analysis
    
    def _calculate_match_confidence(self, match, content: str) -> float:
        """Calculate confidence score for a pattern match"""
        match_length = match.end() - match.start()
        content_length = len(content)
        
        # Base confidence on match length and uniqueness
        length_score = min(1.0, match_length / 100)  # Prefer longer, more specific matches
        
        # Context relevance (check surrounding words)
        context = self._extract_context(content, match.start(), match.end(), window=50)
        context_words = re.findall(r'\b\w+\b', context.lower())
        
        # Words that indicate high confidence
        high_confidence_words = ['hiring', 'job', 'position', 'company', 'team', 'join', 'apply']
        context_score = len([w for w in context_words if w in high_confidence_words]) / len(context_words) if context_words else 0
        
        # Position bias (earlier matches slightly preferred)
        position_bias = 1.0 - (match.start() / content_length) * 0.2
        
        return min(1.0, (length_score * 0.4 + context_score * 0.4 + position_bias * 0.2))
    
    def _extract_context(self, content: str, start: int, end: int, window: int = 100) -> str:
        """Extract context around a match"""
        context_start = max(0, start - window)
        context_end = min(len(content), end + window)
        return content[context_start:context_end]
    
    def _extract_pattern_data(self, match, category: PatternCategory) -> Dict[str, Any]:
        """Extract structured data from a pattern match"""
        data = {}
        
        if category == PatternCategory.CONTACT_DETAILS:
            matched_text = match.group(0)
            if '@' in matched_text:
                data['type'] = 'email'
                data['value'] = matched_text.lower()
            elif re.search(r'\d{10,}', matched_text):
                data['type'] = 'phone'
                data['value'] = re.sub(r'[^\d+]', '', matched_text)
            else:
                data['type'] = 'social'
                data['value'] = matched_text
        
        elif category == PatternCategory.COMPANY_SIZE:
            matched_text = match.group(0)
            numbers = re.findall(r'\d+', matched_text)
            if numbers:
                data['size'] = int(numbers[0])
                data['unit'] = 'employees'
            else:
                data['size_category'] = matched_text.lower()
        
        elif category == PatternCategory.JOB_REQUIREMENTS:
            data['job_keywords'] = re.findall(r'\b\w+\b', match.group(0))
        
        return data
    
    def _get_template_for_content_type(self, content_type: ContentType) -> Optional[str]:
        """Get appropriate extraction template for content type"""
        template_map = {
            ContentType.JOB_DESCRIPTION: 'job_posting',
            ContentType.COMPANY_PROFILE: 'company_profile',
            ContentType.CONTACT_INFO: 'contact_info',
            ContentType.WEBSITE_CONTENT: 'company_profile',
            ContentType.PRESS_RELEASE: 'company_profile'
        }
        return template_map.get(content_type)
    
    def _extract_with_template(self, content: str, template: ExtractionTemplate) -> Tuple[Dict[str, Any], List[ValidationResult]]:
        """Extract data using an extraction template"""
        extracted_data = {}
        validation_results = []
        
        for field_name, rules in template.extraction_rules.items():
            pattern_indices = rules['pattern']
            if isinstance(pattern_indices, int):
                pattern_indices = [pattern_indices]
            
            field_values = []
            for pattern_idx in pattern_indices:
                if pattern_idx < len(template.patterns):
                    pattern = template.patterns[pattern_idx]
                    matches = pattern.findall(content)
                    
                    if rules.get('multiple', False):
                        field_values.extend(matches)
                    else:
                        field_values.extend(matches[:1])  # Take first match only
            
            if field_values:
                # Use first valid value
                for value in field_values:
                    validation_result = self._validate_field(value, rules, template.validation_rules)
                    validation_results.append(validation_result)
                    
                    if validation_result.is_valid:
                        if rules.get('multiple', False):
                            extracted_data[field_name] = field_values
                        else:
                            extracted_data[field_name] = value
                        break
        
        return extracted_data, validation_results
    
    def _validate_field(self, value: Any, rules: Dict[str, Any], validation_rules: Dict[str, callable]) -> ValidationResult:
        """Validate a field value"""
        validation_type = rules.get('validation')
        errors = []
        
        if validation_type and validation_type in validation_rules:
            validator = validation_rules[validation_type]
            try:
                is_valid = validator(value)
                confidence = 1.0 if is_valid else 0.0
            except Exception as e:
                is_valid = False
                confidence = 0.0
                errors.append(f"Validation error: {e}")
        else:
            # No validation specified, assume valid
            is_valid = True
            confidence = 0.8
        
        if rules.get('required', False) and not value:
            is_valid = False
            errors.append("Required field is empty")
        
        return ValidationResult(
            field_name=rules.get('field_name', 'unknown'),
            value=value,
            is_valid=is_valid,
            confidence=confidence,
            validation_errors=errors
        )
    
    def _calculate_extraction_confidence(self, validation_results: List[ValidationResult]) -> float:
        """Calculate overall confidence score for extraction"""
        if not validation_results:
            return 0.0
        
        valid_results = [r for r in validation_results if r.is_valid]
        total_confidence = sum(r.confidence for r in validation_results)
        
        # Weight by validity and number of validations
        validity_score = len(valid_results) / len(validation_results)
        confidence_score = total_confidence / len(validation_results)
        
        return (validity_score * 0.6 + confidence_score * 0.4)
    
    def _analyze_content_categories(self, content: str, matches: List[PatternMatch]) -> Dict[str, Any]:
        """Analyze content for category-specific insights"""
        analysis = {
            'hiring_signals_count': 0,
            'contact_info_count': 0,
            'company_signals': [],
            'job_signals': [],
            'industry_keywords': []
        }
        
        for match in matches:
            if match.category == PatternCategory.HIRING_SIGNALS:
                analysis['hiring_signals_count'] += 1
            elif match.category == PatternCategory.CONTACT_DETAILS:
                analysis['contact_info_count'] += 1
            elif match.category == PatternCategory.COMPANY_INFO:
                analysis['company_signals'].append(match.matched_text)
            elif match.category == PatternCategory.JOB_REQUIREMENTS:
                analysis['job_signals'].append(match.matched_text)
            elif match.category == PatternCategory.INDUSTRY_SIGNALS:
                analysis['industry_keywords'].extend(match.extracted_data.get('keywords', []))
        
        # Deduplicate lists
        analysis['company_signals'] = list(set(analysis['company_signals']))
        analysis['job_signals'] = list(set(analysis['job_signals']))
        analysis['industry_keywords'] = list(set(analysis['industry_keywords']))
        
        return analysis
    
    def _pattern_match_to_dict(self, match: PatternMatch) -> Dict[str, Any]:
        """Convert PatternMatch to dictionary"""
        return {
            'pattern_name': match.pattern_name,
            'matched_text': match.matched_text,
            'confidence': match.confidence,
            'start_position': match.start_position,
            'end_position': match.end_position,
            'context': match.context,
            'category': match.category.value,
            'extracted_data': match.extracted_data
        }
    
    def _validation_to_dict(self, validation: ValidationResult) -> Dict[str, Any]:
        """Convert ValidationResult to dictionary"""
        return {
            'field_name': validation.field_name,
            'value': validation.value,
            'is_valid': validation.is_valid,
            'confidence': validation.confidence,
            'validation_errors': validation.validation_errors
        }

# Global instance
pattern_matcher = PatternMatcher()
