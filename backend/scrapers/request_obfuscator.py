"""
Request Pattern Obfuscation system for human-like behavior simulation.
Implements randomized timing, mouse movements, scrolling, and interaction patterns.
"""
import logging
import time
import random
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class InteractionType(Enum):
    """Types of user interactions"""
    CLICK = "click"
    HOVER = "hover"
    SCROLL = "scroll"
    TYPE = "type"
    FOCUS = "focus"
    BLUR = "blur"

class TimingPattern(Enum):
    """Human timing patterns"""
    FAST = "fast"  # Quick interactions
    NORMAL = "normal"  # Average user
    SLOW = "slow"  # Careful/cautious user
    RANDOM = "random"  # Unpredictable

@dataclass
class InteractionEvent:
    """Represents a user interaction event"""
    interaction_type: InteractionType
    timestamp: float
    position: Optional[Tuple[int, int]] = None
    duration: Optional[float] = None
    target_element: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

@dataclass
class RequestPattern:
    """Complete request pattern configuration"""
    timing_pattern: TimingPattern
    mouse_movements: List[InteractionEvent]
    scroll_events: List[InteractionEvent]
    focus_events: List[InteractionEvent]
    typing_delays: List[float]
    page_load_wait: float
    interaction_delay: float
    session_duration: float

class RequestObfuscator:
    """
    Simulates human-like browsing patterns to avoid detection
    """
    
    def __init__(self):
        self.patterns: Dict[str, RequestPattern] = {}
        self.current_pattern: Optional[str] = None
        
        # Timing configurations for different user types
        self.timing_configs = {
            TimingPattern.FAST: {
                'page_load_wait': (0.5, 2.0),
                'interaction_delay': (0.1, 0.5),
                'session_duration': (30, 120),
                'mouse_speed': (800, 1200),  # pixels per second
                'typing_speed': (100, 150),  # chars per minute
                'scroll_speed': (300, 500)   # pixels per second
            },
            TimingPattern.NORMAL: {
                'page_load_wait': (1.0, 4.0),
                'interaction_delay': (0.3, 1.2),
                'session_duration': (60, 300),
                'mouse_speed': (400, 800),
                'typing_speed': (40, 80),
                'scroll_speed': (150, 300)
            },
            TimingPattern.SLOW: {
                'page_load_wait': (2.0, 8.0),
                'interaction_delay': (0.8, 3.0),
                'session_duration': (120, 600),
                'mouse_speed': (200, 400),
                'typing_speed': (20, 40),
                'scroll_speed': (50, 150)
            }
        }
        
        self._initialize_patterns()
    
    def _initialize_patterns(self) -> None:
        """Create initial request patterns"""
        pattern_names = ['aggressive', 'casual', 'thorough', 'mobile', 'desktop_fast', 'desktop_slow']
        
        for pattern_name in pattern_names:
            pattern = self._generate_pattern(pattern_name)
            self.patterns[pattern_name] = pattern
        
        logger.info(f"Initialized {len(self.patterns)} request patterns")
    
    def get_pattern(self, pattern_name: Optional[str] = None, timing: Optional[TimingPattern] = None) -> RequestPattern:
        """
        Get a request pattern configuration
        
        Args:
            pattern_name: Specific pattern name
            timing: Preferred timing pattern
            
        Returns:
            RequestPattern configuration
        """
        if pattern_name and pattern_name in self.patterns:
            return self.patterns[pattern_name]
        
        # Generate new pattern if requested timing differs
        if timing:
            pattern_name = f"custom_{timing.value}"
            if pattern_name not in self.patterns:
                self.patterns[pattern_name] = self._generate_pattern(pattern_name, timing)
            return self.patterns[pattern_name]
        
        # Default to random pattern
        if not self.current_pattern:
            self.current_pattern = random.choice(list(self.patterns.keys()))
        
        return self.patterns[self.current_pattern]
    
    def _generate_pattern(self, name: str, timing: Optional[TimingPattern] = None) -> RequestPattern:
        """Generate a request pattern"""
        
        # Determine timing pattern
        if not timing:
            if 'fast' in name:
                timing = TimingPattern.FAST
            elif 'slow' in name:
                timing = TimingPattern.SLOW
            else:
                timing = TimingPattern.NORMAL
        
        config = self.timing_configs[timing]
        
        # Generate mouse movements
        mouse_movements = self._generate_mouse_movements(config)
        
        # Generate scroll events
        scroll_events = self._generate_scroll_events(config)
        
        # Generate focus events
        focus_events = self._generate_focus_events(config)
        
        # Generate typing delays
        typing_delays = self._generate_typing_delays(config)
        
        pattern = RequestPattern(
            timing_pattern=timing,
            mouse_movements=mouse_movements,
            scroll_events=scroll_events,
            focus_events=focus_events,
            typing_delays=typing_delays,
            page_load_wait=random.uniform(*config['page_load_wait']),
            interaction_delay=random.uniform(*config['interaction_delay']),
            session_duration=random.uniform(*config['session_duration'])
        )
        
        return pattern
    
    def _generate_mouse_movements(self, config: Dict[str, Tuple[float, float]]) -> List[InteractionEvent]:
        """Generate realistic mouse movement patterns"""
        movements = []
        
        # Generate 5-15 mouse movements per pattern
        num_movements = random.randint(5, 15)
        
        for i in range(num_movements):
            # Random screen positions
            x = random.randint(0, 1920)
            y = random.randint(0, 1080)
            
            # Random timing within session
            timestamp = random.uniform(0, config['session_duration'][1])
            
            # Movement duration based on distance from previous position
            if movements:
                prev_x, prev_y = movements[-1].position
                distance = ((x - prev_x) ** 2 + (y - prev_y) ** 2) ** 0.5
                duration = distance / random.uniform(*config['mouse_speed'])
            else:
                duration = random.uniform(0.1, 0.5)
            
            movement = InteractionEvent(
                interaction_type=InteractionType.HOVER,
                timestamp=timestamp,
                position=(x, y),
                duration=duration,
                target_element=f"element_{i}"
            )
            
            movements.append(movement)
        
        # Sort by timestamp
        movements.sort(key=lambda x: x.timestamp)
        return movements
    
    def _generate_scroll_events(self, config: Dict[str, Tuple[float, float]]) -> List[InteractionEvent]:
        """Generate scroll events"""
        scroll_events = []
        
        # Generate 3-8 scroll events
        num_scrolls = random.randint(3, 8)
        
        for i in range(num_scrolls):
            timestamp = random.uniform(5, config['session_duration'][1] - 5)
            
            # Scroll direction and amount
            direction = random.choice(['down', 'up'])
            amount = random.randint(200, 800)
            
            scroll_event = InteractionEvent(
                interaction_type=InteractionType.SCROLL,
                timestamp=timestamp,
                duration=random.uniform(0.5, 2.0),
                additional_data={
                    'direction': direction,
                    'amount': amount,
                    'speed': random.uniform(*config['scroll_speed'])
                }
            )
            
            scroll_events.append(scroll_event)
        
        scroll_events.sort(key=lambda x: x.timestamp)
        return scroll_events
    
    def _generate_focus_events(self, config: Dict[str, Tuple[float, float]]) -> List[InteractionEvent]:
        """Generate focus/blur events"""
        focus_events = []
        
        # Generate focus events for form elements
        form_elements = ['input[name="q"]', 'input[type="email"]', 'textarea', 'select']
        
        for element in form_elements:
            # Focus event
            focus_time = random.uniform(10, config['session_duration'][1] - 10)
            focus_event = InteractionEvent(
                interaction_type=InteractionType.FOCUS,
                timestamp=focus_time,
                target_element=element
            )
            
            # Blur event (if user leaves the field)
            if random.random() > 0.3:  # 70% chance of blur
                blur_time = focus_time + random.uniform(1, 10)
                blur_event = InteractionEvent(
                    interaction_type=InteractionType.BLUR,
                    timestamp=blur_time,
                    target_element=element
                )
                focus_events.extend([focus_event, blur_event])
            else:
                focus_events.append(focus_event)
        
        focus_events.sort(key=lambda x: x.timestamp)
        return focus_events
    
    def _generate_typing_delays(self, config: Dict[str, Tuple[float, float]]) -> List[float]:
        """Generate realistic typing delays"""
        delays = []
        
        # Generate delays for 10-50 characters
        num_chars = random.randint(10, 50)
        
        for i in range(num_chars):
            # Typing speed with some randomness
            base_delay = 60.0 / random.uniform(*config['typing_speed'])  # seconds per character
            
            # Add hesitation for certain characters
            if random.random() < 0.1:  # 10% chance of longer pause
                delay = base_delay * random.uniform(2, 5)
            else:
                delay = base_delay * random.uniform(0.8, 1.5)
            
            delays.append(delay)
        
        return delays
    
    async def simulate_interactions(self, pattern: RequestPattern, page) -> None:
        """
        Simulate human-like interactions on a page
        
        Args:
            pattern: Request pattern to follow
            page: Playwright page object
        """
        try:
            logger.info("Starting interaction simulation...")
            
            # Wait for page load
            await asyncio.sleep(pattern.page_load_wait)
            
            # Simulate mouse movements
            for movement in pattern.mouse_movements:
                try:
                    if movement.position:
                        x, y = movement.position
                        await page.mouse.move(x, y, steps=random.randint(5, 15))
                        await asyncio.sleep(movement.duration or 0.1)
                except Exception as e:
                    logger.debug(f"Mouse movement failed: {e}")
            
            # Simulate scrolling
            for scroll in pattern.scroll_events:
                try:
                    if scroll.additional_data:
                        direction = scroll.additional_data.get('direction', 'down')
                        amount = scroll.additional_data.get('amount', 300)
                        
                        if direction == 'down':
                            await page.evaluate(f"window.scrollBy(0, {amount})")
                        else:
                            await page.evaluate(f"window.scrollBy(0, -{amount})")
                        
                        await asyncio.sleep(scroll.duration or 1.0)
                except Exception as e:
                    logger.debug(f"Scroll failed: {e}")
            
            # Simulate focus events
            for focus_event in pattern.focus_events:
                try:
                    if focus_event.target_element:
                        if focus_event.interaction_type == InteractionType.FOCUS:
                            await page.focus(focus_event.target_element)
                        elif focus_event.interaction_type == InteractionType.BLUR:
                            # Blur by focusing another element
                            await page.focus('body')
                        
                        await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"Focus event failed: {e}")
            
            # Random interaction delay
            await asyncio.sleep(pattern.interaction_delay)
            
            logger.info("Interaction simulation completed")
            
        except Exception as e:
            logger.error(f"Interaction simulation failed: {e}")
    
    def simulate_typing(self, text: str, pattern: RequestPattern) -> List[float]:
        """
        Simulate typing delays for text input
        
        Args:
            text: Text to type
            pattern: Request pattern
            
        Returns:
            List of delays between characters
        """
        delays = []
        
        for i, char in enumerate(text):
            if i < len(pattern.typing_delays):
                delay = pattern.typing_delays[i]
            else:
                # Generate new delay if we run out
                delay = random.uniform(0.05, 0.2)
            
            # Special delays for certain characters
            if char in [' ', '.', ',', '!', '?']:
                delay *= 2
            
            delays.append(delay)
        
        return delays
    
    def get_request_delay(self, timing: TimingPattern = TimingPattern.NORMAL) -> float:
        """
        Get appropriate delay between requests
        
        Args:
            timing: Timing pattern
            
        Returns:
            Delay in seconds
        """
        config = self.timing_configs[timing]
        
        # Base delay between requests
        base_delay = random.uniform(*config['interaction_delay'])
        
        # Add random jitter
        jitter = random.uniform(-0.5, 0.5) * base_delay
        delay = base_delay + jitter
        
        # Ensure minimum delay
        return max(0.1, delay)
    
    def should_add_human_behavior(self) -> bool:
        """Determine if human behavior should be added (to avoid detection)"""
        return random.random() > 0.2  # 80% chance of adding human behavior

# Global instance
request_obfuscator = RequestObfuscator()
