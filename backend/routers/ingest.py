"""Data ingest - OCR, file uploads, contact extraction, RSS feeds, and more."""

from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
import os
import shutil
import subprocess
import tempfile
from PIL import Image
import io
import re
import logging
import csv
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from database import SessionLocal
from routers.classify import classify_signal as classify_signal_func
from routers.classify import SignalInput

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import phonenumbers
    from phonenumbers import NumberParseException
except ImportError:
    phonenumbers = None

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import httpx
except ImportError:
    httpx = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class OCRResult(BaseModel):
    extracted_text: str
    detected_emails: list
    detected_phones: list
    detected_names: list
    detected_company: Optional[str]

def extract_emails(text: str) -> list:
    """Extract email addresses from text using regex."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)

def normalize_phone_number(phone: str, default_region: str = "IN") -> Optional[str]:
    """
    Normalize a phone number to E.164 format using phonenumbers library.
    Returns normalized number or None if invalid.
    """
    if not phonenumbers:
        # Fallback: simple cleaning
        cleaned = re.sub(r'[^\d+]', '', phone)
        return cleaned if len(cleaned) >= 10 else None

    try:
        # Parse the number
        parsed = phonenumbers.parse(phone, default_region)

        # Validate
        if phonenumbers.is_valid_number(parsed):
            # Return in E.164 format (e.g., +919876543210)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        return None
    except NumberParseException:
        return None

def ocr_image_with_tesseract(image: Image.Image, lang: str = "eng") -> str:
    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        raise RuntimeError("Tesseract binary not installed or not on PATH")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            temp_path = tmp.name

        # Ensure image is in a supported mode for PNG
        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")

        image.save(temp_path, format="PNG")

        result = subprocess.run(
            [tesseract_cmd, temp_path, "stdout", "-l", lang],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or "Tesseract OCR failed").strip())

        return (result.stdout or "").strip()
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

def extract_phones(text: str) -> list:
    """Extract and normalize phone numbers from text using regex."""
    phone_patterns = [
        r'\+91[-.\s]?\d{10}',  # +91 followed by 10 digits
        r'91[-.\s]?\d{10}',  # 91 followed by 10 digits
        r'\b\d{10}\b',  # 10 consecutive digits
        r'[6-9]\d{9}',  # Indian phone starting with 6-9
    ]
    phones = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        phones.extend(matches)

    # Normalize and deduplicate
    normalized = []
    seen = set()
    for phone in phones:
        norm = normalize_phone_number(phone)
        if norm and norm not in seen:
            normalized.append(norm)
            seen.add(norm)

    return normalized

def extract_names(text: str) -> list:
    """Simple name extraction - look for capitalized word sequences."""
    # Very basic: find sequences of capitalized words
    name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    return re.findall(name_pattern, text)[:5]  # Return max 5

def extract_company(text: str) -> Optional[str]:
    """Try to extract company name from text."""
    # Look for common patterns: "Company:", "at X", "X Ltd", "X Pvt Ltd"
    patterns = [
        r'(?:Company|company|business|firm|organization)\s*:?\s*([A-Za-z0-9\s&.,]+)',
        r'at\s+([A-Za-z0-9\s&]+?)(?:\s+[,.]|$)',
        r'([A-Za-z0-9\s&]+?)\s+(?:Pvt|Ltd|Inc|Corporation|Services)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None

@router.post("/ocr", response_model=OCRResult)
async def ingest_ocr(
    file: UploadFile = File(...),
    use_ocr_for_pdf: bool = False,
    db: Session = Depends(get_db),
):
    """
    Upload an image or PDF and extract text.
    For images: use Tesseract OCR.
    For PDFs: extract text directly (faster) or use pdfplumber + OCR for scanned PDFs.
    Also extract contact info (emails, phones, names, company).

    Args:
        file: Image or PDF file
        use_ocr_for_pdf: If True, use pdfplumber + OCR for scanned PDFs (slower but works on scanned docs)
    """
    try:
        # Read file
        contents = await file.read()

        # Extract text based on file type
        if file.content_type.startswith("image"):
            # Image handling: use Tesseract OCR
            image = Image.open(io.BytesIO(contents))
            extracted_text = ocr_image_with_tesseract(image, lang='eng')
            logger.info(f"OCR'd image: {file.filename}")

        elif file.content_type == "application/pdf" or file.filename.endswith(".pdf"):
            # PDF handling with two modes
            if use_ocr_for_pdf and pdfplumber:
                # Mode 1: pdfplumber + OCR (for scanned PDFs/business cards)
                try:
                    pdf_file = io.BytesIO(contents)
                    pages_text = []

                    with pdfplumber.open(pdf_file) as pdf:
                        for page_num, page in enumerate(pdf.pages):
                            # Try text extraction first
                            text = page.extract_text()

                            # If no text found, convert to image and OCR
                            if not text or len(text.strip()) < 10:
                                try:
                                    # Convert page to image and OCR
                                    img = page.to_image(resolution=300)
                                    pil_img = img.original
                                    text = ocr_image_with_tesseract(pil_img, lang='eng')
                                    logger.info(f"OCR'd PDF page {page_num + 1} of {file.filename}")
                                except Exception as ocr_err:
                                    logger.warning(f"OCR failed for page {page_num + 1}: {ocr_err}")
                                    text = ""

                            if text:
                                pages_text.append(text)

                    extracted_text = "\n".join(pages_text)
                    logger.info(f"Processed {len(pdf.pages)} pages of {file.filename} with pdfplumber+OCR")

                except Exception as pdf_err:
                    raise HTTPException(status_code=400, detail=f"Failed to parse PDF with pdfplumber: {str(pdf_err)}")

            else:
                # Mode 2: Fast text extraction with pypdf (default)
                if PdfReader is None:
                    raise HTTPException(status_code=500, detail="PDF support not available. Install pypdf: pip install pypdf")

                try:
                    pdf_file = io.BytesIO(contents)
                    reader = PdfReader(pdf_file)
                    pages_text = []
                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text:
                            pages_text.append(text)
                    extracted_text = "\n".join(pages_text)
                    logger.info(f"Extracted text from {len(reader.pages)} pages of {file.filename}")
                except Exception as pdf_err:
                    # If pypdf fails, suggest using OCR mode
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to parse PDF: {str(pdf_err)}. Try use_ocr_for_pdf=true for scanned PDFs."
                    )
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use image (.jpg, .png, .gif) or PDF.")

        # Clean up extracted text
        extracted_text = extracted_text.strip()

        if not extracted_text:
            raise HTTPException(status_code=400, detail="Failed to extract text from file. Try use_ocr_for_pdf=true for scanned PDFs.")

        # Extract contact info
        emails = extract_emails(extracted_text)
        phones = extract_phones(extracted_text)
        names = extract_names(extracted_text)
        company = extract_company(extracted_text)

        return OCRResult(
            extracted_text=extracted_text,
            detected_emails=emails,
            detected_phones=phones,
            detected_names=names,
            detected_company=company,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OCR ingest: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@router.post("/ocr-and-classify")
async def ingest_ocr_and_classify(
    file: UploadFile = File(...),
    company_name: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Upload a file (image or PDF), extract text, and immediately classify as a lead.
    If score > threshold, queue dossier generation (background task).
    """
    try:
        # Step 1: Extract text
        contents = await file.read()

        if file.content_type.startswith("image"):
            # Image: OCR with Tesseract
            image = Image.open(io.BytesIO(contents))
            extracted_text = ocr_image_with_tesseract(image, lang='eng')
            source_type = "ocr_image"
        elif file.content_type == "application/pdf" or file.filename.endswith(".pdf"):
            # PDF: text extraction
            if PdfReader is None:
                raise HTTPException(status_code=500, detail="PDF support not available. Install: pip install pypdf")

            try:
                pdf_file = io.BytesIO(contents)
                reader = PdfReader(pdf_file)
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                extracted_text = "\n".join(pages_text)
                source_type = "ocr_pdf"
            except Exception as pdf_err:
                raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(pdf_err)}")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use image or PDF.")

        extracted_text = extracted_text.strip()

        if not extracted_text:
            raise HTTPException(status_code=400, detail="Failed to extract text from file")

        # Step 2: Classify
        signal = SignalInput(
            signal_text=extracted_text,
            source_type=source_type,
            company_name=company_name or extract_company(extracted_text),
        )

        result = await classify_signal_func(signal, background_tasks, db)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OCR classify: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.post("/csv")
async def ingest_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Bulk ingest from CSV and classify each signal.
    Expected columns: company_name, company_website (optional), signal_text

    Returns summary of created leads.
    """
    try:
        import io as stdio

        contents = await file.read()
        stream = stdio.StringIO(contents.decode("utf8"))
        csv_reader = csv.DictReader(stream)

        # Validate headers
        if not csv_reader.fieldnames or "signal_text" not in csv_reader.fieldnames:
            raise HTTPException(
                status_code=400,
                detail=f"CSV must have 'signal_text' column. Found columns: {csv_reader.fieldnames}. "
                        "Required: signal_text, company_name (optional), company_website (optional)"
            )

        results = []
        processed_count = 0

        for row in csv_reader:
            signal_text = row.get("signal_text", "").strip()
            company_name = row.get("company_name", "").strip()

            if not signal_text:
                continue  # Skip empty rows

            processed_count += 1

            # Create signal input
            signal = SignalInput(
                signal_text=signal_text,
                source_type="csv",
                company_name=company_name or None,
                company_website=row.get("company_website") or None,
            )

            # Classify synchronously (for CSV, we do batch processing)
            try:
                result = await classify_signal_func(signal, background_tasks, db)
                results.append({
                    "company": company_name,
                    "score": result.total_score,
                    "bucket": result.score_bucket,
                    "lead_id": result.lead_id,
                    "status": "created",
                })
            except Exception as e:
                logger.error(f"Error classifying CSV row {processed_count}: {e}")
                results.append({
                    "company": company_name,
                    "status": "error",
                    "error": str(e),
                })

        return {
            "total_processed": processed_count,
            "total_created": len([r for r in results if r.get("status") == "created"]),
            "results": results,
            "message": f"Processed {processed_count} rows, created {len([r for r in results if r.get('status') == 'created'])} leads",
        }

    except Exception as e:
        logger.error(f"Error in CSV ingest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEW ENDPOINTS - Enhanced Data Ingestion
# ============================================================================

class JobCSVRow(BaseModel):
    """Schema for job CSV rows."""
    company_name: str
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    posted_at: Optional[str] = None
    company_website: Optional[str] = None


@router.post("/jobs/csv")
async def ingest_jobs_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    CSV job importer - Accept CSV files with job-specific columns.
    Expected columns: company_name, title, description, location, posted_at
    Parse each row into a JobSignal and feed into classify_signal.

    Returns summary of created leads.
    """
    try:
        import io as stdio

        contents = await file.read()
        stream = stdio.StringIO(contents.decode("utf8"))
        csv_reader = csv.DictReader(stream)

        results = []
        processed_count = 0

        for row in csv_reader:
            company_name = row.get("company_name", "").strip()
            title = row.get("title", "").strip()
            description = row.get("description", "").strip()
            location = row.get("location", "").strip()
            posted_at = row.get("posted_at", "").strip()

            if not company_name or not description:
                continue  # Skip rows without essential data

            processed_count += 1

            # Build job signal text
            signal_parts = []
            if title:
                signal_parts.append(f"Job Title: {title}")
            if location:
                signal_parts.append(f"Location: {location}")
            if posted_at:
                signal_parts.append(f"Posted: {posted_at}")
            signal_parts.append(f"Description: {description}")

            signal_text = "\n".join(signal_parts)

            # Create signal input
            signal = SignalInput(
                signal_text=signal_text,
                source_type="job_post",
                company_name=company_name,
                company_website=row.get("company_website") or None,
            )

            # Classify synchronously
            try:
                result = await classify_signal_func(signal, background_tasks, db)
                results.append({
                    "company": company_name,
                    "title": title,
                    "score": result.total_score,
                    "bucket": result.score_bucket,
                    "lead_id": result.lead_id,
                    "status": "created",
                })
            except Exception as e:
                logger.error(f"Error classifying job row {processed_count}: {e}")
                results.append({
                    "company": company_name,
                    "title": title,
                    "status": "error",
                    "error": str(e),
                })

        return {
            "total_processed": processed_count,
            "total_created": len([r for r in results if r.get("status") == "created"]),
            "results": results,
            "message": f"Processed {processed_count} job rows, created {len([r for r in results if r.get('status') == 'created'])} leads",
        }

    except Exception as e:
        logger.error(f"Error in job CSV ingest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class JSONSignal(BaseModel):
    """Schema for bulk JSON import."""
    company_name: str
    signal_text: str
    company_website: Optional[str] = None
    source_type: Optional[str] = "json"
    metadata: Optional[Dict[str, Any]] = {}


@router.post("/json")
async def ingest_json_bulk(
    signals: List[JSONSignal],
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Bulk JSON import - Accept a JSON array of signals.
    Allows integration with third-party tools.

    Example:
    [
        {
            "company_name": "Acme Corp",
            "signal_text": "Hiring marketing manager...",
            "company_website": "https://acme.com",
            "metadata": {"source": "api"}
        }
    ]
    """
    try:
        results = []
        processed_count = 0

        for idx, json_signal in enumerate(signals):
            if not json_signal.company_name or not json_signal.signal_text:
                continue

            processed_count += 1

            # Create signal input
            signal = SignalInput(
                signal_text=json_signal.signal_text,
                source_type=json_signal.source_type or "json",
                company_name=json_signal.company_name,
                company_website=json_signal.company_website,
            )

            # Classify
            try:
                result = await classify_signal_func(signal, background_tasks, db)
                results.append({
                    "company": json_signal.company_name,
                    "score": result.total_score,
                    "bucket": result.score_bucket,
                    "lead_id": result.lead_id,
                    "status": "created",
                })
            except Exception as e:
                logger.error(f"Error classifying JSON signal {idx}: {e}")
                results.append({
                    "company": json_signal.company_name,
                    "status": "error",
                    "error": str(e),
                })

        return {
            "total_processed": processed_count,
            "total_created": len([r for r in results if r.get("status") == "created"]),
            "results": results,
            "message": f"Processed {processed_count} signals, created {len([r for r in results if r.get('status') == 'created'])} leads",
        }

    except Exception as e:
        logger.error(f"Error in JSON bulk ingest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LinkedInPostInput(BaseModel):
    """Schema for LinkedIn post URL input."""
    post_url: str
    company_name: Optional[str] = None


@router.post("/linkedin-post")
async def ingest_linkedin_post(
    input_data: LinkedInPostInput,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Drag-and-drop LinkedIn posts - Accept a LinkedIn job post URL.
    If the post is public, fetch its HTML, extract text and classify it.

    Note: Only works for publicly visible job posts (not behind login).
    """
    if not httpx:
        raise HTTPException(status_code=500, detail="httpx not available. Install: pip install httpx")
    if not BeautifulSoup:
        raise HTTPException(status_code=500, detail="beautifulsoup4 not available. Install: pip install beautifulsoup4")

    try:
        # Fetch the LinkedIn post
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = await client.get(input_data.post_url, headers=headers, follow_redirects=True)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch LinkedIn post. Status: {response.status_code}. Post may be private or require login."
                )

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract text (LinkedIn's structure varies, try multiple selectors)
        text_elements = []

        # Try job description containers
        for selector in [
            'div.description__text',
            'div.show-more-less-html__markup',
            'div[class*="description"]',
            'article',
            'main',
        ]:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True, separator='\n')
                if text and len(text) > 50:
                    text_elements.append(text)

        # Fallback: get all text
        if not text_elements:
            text_elements = [soup.get_text(strip=True, separator='\n')]

        extracted_text = "\n\n".join(text_elements)

        if not extracted_text or len(extracted_text) < 20:
            raise HTTPException(
                status_code=400,
                detail="Could not extract meaningful text from LinkedIn post. Post may require login or use dynamic loading."
            )

        # Try to extract company name from page if not provided
        company_name = input_data.company_name
        if not company_name:
            # Try to find company name in page
            company_elem = soup.select_one('a.topcard__org-name-link, a[data-tracking-control-name*="company"]')
            if company_elem:
                company_name = company_elem.get_text(strip=True)

        # Classify
        signal = SignalInput(
            signal_text=extracted_text,
            source_type="linkedin_post",
            company_name=company_name,
            source_url=input_data.post_url,
        )

        result = await classify_signal_func(signal, background_tasks, db)
        return {
            **result.dict(),
            "extracted_text_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting LinkedIn post: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process LinkedIn post: {str(e)}")


class RSSFeedInput(BaseModel):
    """Schema for RSS feed subscription."""
    feed_url: str
    auto_classify: bool = True
    max_items: int = 20


@router.post("/rss/fetch")
async def fetch_rss_feed(
    input_data: RSSFeedInput,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    RSS/Atom feed monitoring - Fetch and parse RSS/Atom feeds.
    Useful for companies that post jobs via RSS feeds.

    Args:
        feed_url: URL of the RSS/Atom feed
        auto_classify: If True, automatically classify each item
        max_items: Maximum number of items to process (default: 20)
    """
    if not feedparser:
        raise HTTPException(status_code=500, detail="feedparser not available. Install: pip install feedparser")

    try:
        # Parse the feed
        feed = feedparser.parse(input_data.feed_url)

        if feed.bozo:
            # Feed has errors
            logger.warning(f"RSS feed parsing errors: {feed.bozo_exception}")

        if not feed.entries:
            return {
                "feed_title": feed.feed.get("title", "Unknown"),
                "total_items": 0,
                "processed": 0,
                "message": "No items found in feed",
            }

        results = []
        processed_count = 0

        # Process feed items (limit to max_items)
        for entry in feed.entries[:input_data.max_items]:
            # Extract data
            title = entry.get("title", "")
            description = entry.get("description", "") or entry.get("summary", "")
            link = entry.get("link", "")
            published = entry.get("published", "") or entry.get("updated", "")

            # Build signal text
            signal_parts = []
            if title:
                signal_parts.append(f"Title: {title}")
            if published:
                signal_parts.append(f"Published: {published}")
            if description:
                # Clean HTML tags from description
                if BeautifulSoup:
                    clean_desc = BeautifulSoup(description, 'html.parser').get_text()
                    signal_parts.append(f"Description: {clean_desc}")
                else:
                    signal_parts.append(f"Description: {description}")

            signal_text = "\n".join(signal_parts)

            if not signal_text or len(signal_text) < 20:
                continue

            processed_count += 1

            # Auto-classify if enabled
            if input_data.auto_classify:
                try:
                    signal = SignalInput(
                        signal_text=signal_text,
                        source_type="rss_feed",
                        source_url=link,
                    )

                    result = await classify_signal_func(signal, background_tasks, db)
                    results.append({
                        "title": title,
                        "link": link,
                        "score": result.total_score,
                        "bucket": result.score_bucket,
                        "lead_id": result.lead_id,
                        "status": "classified",
                    })
                except Exception as e:
                    logger.error(f"Error classifying RSS item: {e}")
                    results.append({
                        "title": title,
                        "link": link,
                        "status": "error",
                        "error": str(e),
                    })
            else:
                # Just return the parsed data
                results.append({
                    "title": title,
                    "link": link,
                    "published": published,
                    "text_preview": signal_text[:200] + "..." if len(signal_text) > 200 else signal_text,
                    "status": "parsed",
                })

        return {
            "feed_title": feed.feed.get("title", "Unknown"),
            "feed_link": feed.feed.get("link", ""),
            "total_items": len(feed.entries),
            "processed": processed_count,
            "auto_classified": input_data.auto_classify,
            "results": results,
            "message": f"Processed {processed_count} items from RSS feed",
        }

    except Exception as e:
        logger.error(f"Error fetching RSS feed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process RSS feed: {str(e)}")
