"""
Browser Fingerprint Rotation system for anti-detection evasion.
Dynamically generates user agents, spoofs canvas fingerprints, and randomizes browser properties.
"""
import logging
import time
import random
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class BrowserType(Enum):
    """Browser types for fingerprinting"""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"

class Platform(Enum):
    """Operating system platforms"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"

@dataclass
class BrowserFingerprint:
    """Complete browser fingerprint configuration"""
    user_agent: str
    platform: str
    vendor: str
    language: str
    languages: List[str]
    timezone: str
    screen_resolution: str
    viewport: str
    color_depth: int
    pixel_ratio: float
    hardware_concurrency: int
    memory_gb: float
    do_not_track: Optional[str]
    cookie_enabled: bool
    plugins: List[str]
    webgl_renderer: str
    webgl_vendor: str
    canvas_fingerprint: str
    web_rtc_enabled: bool
    touch_support: bool
    browser_type: BrowserType
    platform_type: Platform

class FingerprintManager:
    """
    Generates and rotates browser fingerprints to avoid detection
    """
    
    def __init__(self):
        self.fingerprints: List[BrowserFingerprint] = []
        self.current_index = 0
        self.rotation_interval = 300  # 5 minutes
        self.last_rotation = 0
        
        # Browser version ranges for realistic fingerprints
        self.browser_versions = {
            BrowserType.CHROME: [(120, 128), (119, 127), (118, 126)],
            BrowserType.FIREFOX: [(121, 125), (120, 124), (119, 123)],
            BrowserType.SAFARI: [(17, 18), (16, 17), (15, 16)],
            BrowserType.EDGE: [(120, 128), (119, 127), (118, 126)]
        }
        
        # Platform distributions for realism
        self.platform_weights = {
            Platform.WINDOWS: 0.65,
            Platform.MACOS: 0.25,
            Platform.LINUX: 0.08,
            Platform.ANDROID: 0.015,
            Platform.IOS: 0.005
        }
        
        self._initialize_fingerprints()
    
    def _initialize_fingerprints(self) -> None:
        """Create initial set of browser fingerprints"""
        # Create 50 different fingerprints for rotation
        for i in range(50):
            fingerprint = self._generate_fingerprint(i)
            self.fingerprints.append(fingerprint)
        
        logger.info(f"Initialized {len(self.fingerprints)} browser fingerprints")
    
    def get_fingerprint(self, browser_type: Optional[BrowserType] = None, platform: Optional[Platform] = None) -> BrowserFingerprint:
        """
        Get a browser fingerprint, rotating automatically
        
        Args:
            browser_type: Preferred browser type
            platform: Preferred platform
            
        Returns:
            BrowserFingerprint configuration
        """
        now = time.time()
        
        # Auto-rotate if needed
        if now - self.last_rotation > self.rotation_interval:
            self._rotate_fingerprints()
            self.last_rotation = now
        
        # Find suitable fingerprint
        candidates = self.fingerprints
        
        if browser_type:
            candidates = [f for f in candidates if f.browser_type == browser_type]
            if not candidates:
                # Generate new fingerprint of requested type
                fingerprint = self._generate_fingerprint(random.randint(1000, 9999), browser_type=browser_type)
                self.fingerprints.append(fingerprint)
                return fingerprint
        
        if platform:
            candidates = [f for f in candidates if f.platform_type == platform]
            if not candidates:
                # Generate new fingerprint for requested platform
                fingerprint = self._generate_fingerprint(random.randint(1000, 9999), platform=platform)
                self.fingerprints.append(fingerprint)
                return fingerprint
        
        # Select fingerprint with round-robin rotation
        fingerprint = candidates[self.current_index % len(candidates)]
        self.current_index += 1
        
        return fingerprint
    
    def _rotate_fingerprints(self) -> None:
        """Rotate fingerprints to avoid pattern detection"""
        # Shuffle fingerprints
        random.shuffle(self.fingerprints)
        
        # Update some fingerprints with new versions
        for i in range(min(10, len(self.fingerprints))):
            fingerprint = self.fingerprints[i]
            # Update browser version
            new_version = self._get_random_browser_version(fingerprint.browser_type)
            fingerprint.user_agent = self._generate_user_agent(
                fingerprint.browser_type, 
                new_version, 
                fingerprint.platform_type
            )
            
            # Update canvas fingerprint
            fingerprint.canvas_fingerprint = self._generate_canvas_fingerprint(fingerprint.user_agent)
        
        logger.info("Rotated browser fingerprints")
    
    def _generate_fingerprint(self, seed: int, browser_type: Optional[BrowserType] = None, platform: Optional[Platform] = None) -> BrowserFingerprint:
        """Generate a complete browser fingerprint"""
        
        # Select browser type
        if not browser_type:
            browser_type = random.choice(list(BrowserType))
        
        # Select platform
        if not platform:
            platforms = list(self.platform_weights.keys())
            weights = list(self.platform_weights.values())
            platform = random.choices(platforms, weights=weights)[0]
        
        # Generate components
        version = self._get_random_browser_version(browser_type)
        user_agent = self._generate_user_agent(browser_type, version, platform)
        
        fingerprint = BrowserFingerprint(
            user_agent=user_agent,
            platform=self._get_platform_string(platform),
            vendor=self._get_vendor_string(browser_type),
            language=self._get_language(platform),
            languages=self._get_languages(platform),
            timezone=self._get_timezone(platform),
            screen_resolution=self._get_screen_resolution(platform),
            viewport=self._get_viewport(platform),
            color_depth=self._get_color_depth(platform),
            pixel_ratio=self._get_pixel_ratio(platform),
            hardware_concurrency=self._get_hardware_concurrency(platform),
            memory_gb=self._get_memory_gb(platform),
            do_not_track=self._get_do_not_track(),
            cookie_enabled=True,
            plugins=self._get_plugins(browser_type, platform),
            webgl_renderer=self._get_webgl_renderer(platform),
            webgl_vendor=self._get_webgl_vendor(platform),
            canvas_fingerprint=self._generate_canvas_fingerprint(user_agent),
            web_rtc_enabled=self._get_web_rtc_enabled(),
            touch_support=self._get_touch_support(platform),
            browser_type=browser_type,
            platform_type=platform
        )
        
        return fingerprint
    
    def _get_random_browser_version(self, browser_type: BrowserType) -> str:
        """Get random browser version for realism"""
        versions = self.browser_versions[browser_type]
        major_min, major_max = random.choice(versions)
        major = random.randint(major_min, major_max)
        
        if browser_type == BrowserType.CHROME:
            return f"{major}.0.0.0"
        elif browser_type == BrowserType.FIREFOX:
            return f"{major}.0"
        elif browser_type == BrowserType.SAFARI:
            return f"{major}.0"
        else:  # EDGE
            return f"{major}.0.0.0"
    
    def _generate_user_agent(self, browser_type: BrowserType, version: str, platform: Platform) -> str:
        """Generate realistic user agent string"""
        
        if browser_type == BrowserType.CHROME:
            if platform == Platform.WINDOWS:
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif platform == Platform.MACOS:
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif platform == Platform.LINUX:
                return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif platform == Platform.ANDROID:
                return f"Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36"
            else:  # IOS
                return f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/{version} Mobile/15E148 Safari/604.1"
        
        elif browser_type == BrowserType.FIREFOX:
            if platform == Platform.WINDOWS:
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}"
            elif platform == Platform.MACOS:
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version}) Gecko/20100101 Firefox/{version}"
            elif platform == Platform.LINUX:
                return f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}) Gecko/20100101 Firefox/{version}"
            elif platform == Platform.ANDROID:
                return f"Mozilla/5.0 (Android 10; Mobile; rv:{version}) Gecko/{version} Firefox/{version}"
            else:  # IOS
                return f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X; rv:{version}) Gecko/20100101 Firefox/{version}"
        
        elif browser_type == BrowserType.SAFARI:
            if platform == Platform.MACOS:
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version.split('.')[0]}.0 Safari/605.1.15"
            elif platform == Platform.IOS:
                return f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version.split('.')[0]}.0 Mobile/15E148 Safari/604.1"
            else:
                # Safari on other platforms is rare, fallback to Chrome
                return self._generate_user_agent(BrowserType.CHROME, version, platform)
        
        else:  # EDGE
            if platform == Platform.WINDOWS:
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36 Edg/{version}"
            else:
                # Edge on other platforms is rare, fallback to Chrome
                return self._generate_user_agent(BrowserType.CHROME, version, platform)
    
    def _get_platform_string(self, platform: Platform) -> str:
        """Get platform string for navigator.platform"""
        if platform == Platform.WINDOWS:
            return "Win32"
        elif platform == Platform.MACOS:
            return "MacIntel"
        elif platform == Platform.LINUX:
            return "Linux x86_64"
        elif platform == Platform.ANDROID:
            return "Linux armv8l"
        else:  # IOS
            return "iPhone"
    
    def _get_vendor_string(self, browser_type: BrowserType) -> str:
        """Get navigator.vendor string"""
        if browser_type == BrowserType.CHROME or browser_type == BrowserType.EDGE:
            return "Google Inc."
        elif browser_type == BrowserType.FIREFOX:
            return ""
        else:  # SAFARI
            return "Apple Computer, Inc."
    
    def _get_language(self, platform: Platform) -> str:
        """Get primary language"""
        return "en-US"
    
    def _get_languages(self, platform: Platform) -> List[str]:
        """Get languages array"""
        return ["en-US", "en"]
    
    def _get_timezone(self, platform: Platform) -> str:
        """Get timezone string"""
        timezones = ["America/New_York", "America/Los_Angeles", "Europe/London", 
                    "Europe/Berlin", "Asia/Tokyo"]
        return random.choice(timezones)
    
    def _get_screen_resolution(self, platform: Platform) -> str:
        """Get screen resolution"""
        if platform in [Platform.ANDROID, Platform.IOS]:
            return random.choice(["375x667", "414x896", "390x844"])
        else:
            return random.choice(["1920x1080", "1366x768", "1536x864"])
    
    def _get_viewport(self, platform: Platform) -> str:
        """Get viewport size"""
        if platform in [Platform.ANDROID, Platform.IOS]:
            return random.choice(["375x667", "414x896", "390x844"])
        else:
            return random.choice(["1920x969", "1366x657", "1536x754"])
    
    def _get_color_depth(self, platform: Platform) -> int:
        """Get screen color depth"""
        return random.choice([24, 32])
    
    def _get_pixel_ratio(self, platform: Platform) -> float:
        """Get device pixel ratio"""
        if platform in [Platform.ANDROID, Platform.IOS]:
            return random.choice([2.0, 3.0])
        return 1.0
    
    def _get_hardware_concurrency(self, platform: Platform) -> int:
        """Get navigator.hardwareConcurrency"""
        if platform == Platform.ANDROID:
            return random.choice([4, 6, 8])
        elif platform == Platform.IOS:
            return random.choice([2, 4, 6])
        else:
            return random.choice([4, 8, 12])
    
    def _get_memory_gb(self, platform: Platform) -> float:
        """Get device memory in GB"""
        return random.choice([4.0, 8.0, 16.0])
    
    def _get_do_not_track(self) -> Optional[str]:
        """Get doNotTrack setting"""
        return random.choice([None, "1"])
    
    def _get_plugins(self, browser_type: BrowserType, platform: Platform) -> List[str]:
        """Get browser plugins list"""
        if browser_type == BrowserType.FIREFOX:
            return ["PDF Viewer"]
        elif browser_type == BrowserType.SAFARI:
            return ["WebKit built-in PDF"]
        else:
            return ["Chrome PDF Plugin", "Chromium PDF Plugin"]
    
    def _get_webgl_renderer(self, platform: Platform) -> str:
        """Get WebGL renderer string"""
        if platform == Platform.WINDOWS:
            return "ANGLE (NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)"
        elif platform == Platform.MACOS:
            return "ANGLE (Intel(R) Iris(TM) Graphics 6100)"
        elif platform == Platform.LINUX:
            return "Mesa DRI Intel(R) UHD Graphics 620"
        elif platform == Platform.ANDROID:
            return "Adreno (TM) 650"
        else:  # IOS
            return "Apple A15 GPU"
    
    def _get_webgl_vendor(self, platform: Platform) -> str:
        """Get WebGL vendor string"""
        if platform == Platform.WINDOWS:
            return "Google Inc. (NVIDIA)"
        elif platform == Platform.MACOS:
            return "Google Inc. (Intel)"
        elif platform == Platform.LINUX:
            return "Intel"
        elif platform == Platform.ANDROID:
            return "Qualcomm"
        else:  # IOS
            return "Apple Inc."
    
    def _generate_canvas_fingerprint(self, user_agent: str) -> str:
        """Generate canvas fingerprint based on user agent"""
        import hashlib
        hash_obj = hashlib.md5(user_agent.encode())
        return hash_obj.hexdigest()[:16]
    
    def _get_web_rtc_enabled(self) -> bool:
        """Get WebRTC enabled status"""
        return random.choice([True, False])
    
    def _get_touch_support(self, platform: Platform) -> bool:
        """Get touch support"""
        return platform in [Platform.ANDROID, Platform.IOS]

# Global instance
fingerprint_manager = FingerprintManager()
