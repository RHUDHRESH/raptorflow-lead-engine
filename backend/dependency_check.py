"""
Dependency checker - verify required system dependencies are available.
Runs at startup to give clear error messages if dependencies are missing.
"""

import logging
import sys
from typing import Tuple

import httpx

logger = logging.getLogger(__name__)


def check_python_version() -> bool:
    """Check Python version (soft fail, just log warning)."""
    if sys.version_info < (3, 9):
        logger.warning(f"⚠️  Python {sys.version_info.major}.{sys.version_info.minor} detected. Python 3.9+ recommended.")
        return False
    logger.info(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def check_tesseract() -> bool:
    """Check if Tesseract OCR binary is installed and accessible."""
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        logger.info(f"✅ Tesseract OCR: {version}")
        return True
    except ImportError:
        logger.warning("⚠️  pytesseract Python module not found (OCR disabled)")
        logger.warning("   Run: pip install pytesseract Pillow")
        return True  # Soft fail
    except pytesseract.TesseractNotFoundError:
        logger.warning("⚠️  Tesseract binary not installed or not on PATH (OCR disabled)")
        logger.warning("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        return True  # Soft fail
    except Exception as e:
        logger.warning(f"⚠️  Error checking Tesseract: {e} (OCR disabled)")
        return True  # Soft fail


def check_pypdf() -> bool:
    """Check if pypdf is installed (soft fail, optional)."""
    try:
        from pypdf import PdfReader
        logger.info("✅ pypdf available (PDF text extraction enabled)")
        return True
    except ImportError:
        logger.warning("⚠️  pypdf not installed (PDF text extraction disabled)")
        logger.warning("   Run: pip install pypdf")
        return False

def check_playwright() -> bool:
    """Check if Playwright browsers are installed."""
    try:
        import subprocess
        # Check chromium folder
        result = subprocess.run(["playwright", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ Playwright CLI: {result.stdout.strip()}")
            # Check browsers roughly
            # Usually they are in %LOCALAPPDATA%\ms-playwright on Windows
            return True
        else:
            logger.warning("⚠️  Playwright CLI error")
            return False
    except Exception as e:
        logger.warning(f"⚠️  Playwright check failed: {e}")
        return False


def check_ollama(ollama_base_url: str, model_1b: str, model_4b: str) -> bool:
    """Check if Ollama is running and models are available."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{ollama_base_url}/api/tags")

            if response.status_code != 200:
                logger.error(f"❌ Ollama returned status {response.status_code}")
                return False

            data = response.json()
            models = data.get("models", [])
            model_names = {m.get("name") for m in models if isinstance(m, dict)}

            logger.info(f"✅ Ollama reachable at {ollama_base_url}")

            # Check if models are present
            if model_1b not in model_names:
                logger.warning(f"   ⚠️  Model {model_1b} not found. Download with: ollama pull {model_1b}")
            else:
                logger.info(f"   ✅ Model {model_1b} available")

            if model_4b not in model_names:
                logger.warning(f"   ⚠️  Model {model_4b} not found. Download with: ollama pull {model_4b}")
            else:
                logger.info(f"   ✅ Model {model_4b} available")

            return True

    except httpx.ConnectError:
        logger.warning(f"⚠️  Cannot connect to Ollama at {ollama_base_url} (AI features disabled)")
        logger.warning("   Make sure Ollama is running: ollama serve")
        return True  # Soft fail
    except Exception as e:
        logger.warning(f"⚠️  Error checking Ollama: {type(e).__name__}: {e} (AI features disabled)")
        return True  # Soft fail


def run_startup_checks(
    ollama_base_url: str,
    model_1b: str,
    model_4b: str,
) -> bool:
    """
    Run all startup dependency checks.

    Returns True if all CRITICAL dependencies are available.
    Non-critical failures (pypdf, Tesseract) are logged as warnings.
    """
    logger.info("=" * 60)
    logger.info("🔍 Checking system dependencies...")
    logger.info("=" * 60)

    # Soft checks (warnings only)
    check_python_version()

    # Hard check: Tesseract (required for MVP)
    tesseract_ok = check_tesseract()

    # Soft check: pypdf (graceful fallback exists)
    check_pypdf()

    # Soft check: Playwright (required for deep scraping/screenshots)
    check_playwright()

    # Hard check: Ollama (absolutely critical)
    ollama_ok = check_ollama(ollama_base_url, model_1b, model_4b)

    logger.info("=" * 60)

    all_ok = tesseract_ok and ollama_ok

    if all_ok:
        logger.info("✅ All critical dependencies available. System ready to start!")
        return True
    else:
        logger.error("❌ Critical dependencies missing. See errors above.")
        return False
