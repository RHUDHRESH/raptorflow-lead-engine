"""Database models and initialization."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from config import Settings

settings = Settings()
DATABASE_URL = settings.database_url
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ICPProfile(Base):
    """ICP (Ideal Customer Profile) definition."""
    __tablename__ = "icp_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Firmographics
    size_buckets = Column(JSON, default=[])  # e.g. ["1", "2-5", "6-10", "11-20"]
    industries = Column(JSON, default=[])
    locations = Column(JSON, default=[])  # e.g. ["india"]
    stages = Column(JSON, default=[])  # e.g. ["freelancer", "early-startup", "small-agency"]

    # Marketing pain signals
    hiring_keywords = Column(JSON, default=[])  # e.g. ["marketing manager", "growth hacker"]
    pain_keywords = Column(JSON, default=[])  # e.g. ["lead generation", "scaling ads"]
    channel_preferences = Column(JSON, default=[])  # e.g. ["instagram", "linkedin"]

    # Budget/maturity
    budget_signals = Column(JSON, default=[])  # e.g. ["diy", "1-junior-marketer"]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Company(Base):
    """Company record."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    website = Column(String, nullable=True, unique=True)
    description = Column(Text, nullable=True)

    # Firmographics
    size_bucket = Column(String, nullable=True)  # "1", "2-5", "6-10", "11-20", "unknown"
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, default="india")
    sector = Column(String, nullable=True)

    # Inferred
    marketing_stack_guess = Column(Text, nullable=True)
    is_marketing_pain_clear = Column(Boolean, default=False)
    company_metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contacts = relationship("Contact", back_populates="company")
    signals = relationship("Signal", back_populates="company")
    leads = relationship("Lead", back_populates="company")

class Contact(Base):
    """Individual contact."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    name = Column(String, nullable=True)
    role = Column(String, nullable=True)

    email = Column(String, nullable=True, unique=True, index=True)
    phone_numbers = Column(JSON, default=[])  # Multiple numbers with classifications
    whatsapp_number = Column(String, nullable=True)
    social_links = Column(JSON, default=[])  # LinkedIn, Twitter, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")
    leads = relationship("Lead", back_populates="contact")

class Signal(Base):
    """Raw signal data (job post, website snippet, OCR text, etc)."""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    source_type = Column(String, index=True)  # "job_post", "website", "ocr", "manual", "csv"
    source_url = Column(String, nullable=True)
    raw_text = Column(Text)
    signal_metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="signals")
    lead = relationship("Lead", back_populates="signals")

class Lead(Base):
    """Qualified lead with scores and context."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)

    # Scoring - Enhanced for high-value targeting
    score_icp_fit = Column(Float, default=0)  # 0-50
    score_marketing_pain = Column(Float, default=0)  # 0-40
    score_data_quality = Column(Float, default=0)  # 0-10
    score_executive_level = Column(Float, default=0)  # 0-30 (C-level, VP, Director priority)
    score_budget_potential = Column(Float, default=0)  # 0-20 (budget authority)
    total_score = Column(Float, default=0)  # 0-150 (adjusted for new scores)
    score_bucket = Column(String, default="parked")  # "red_hot", "warm", "nurture", "parked"

    # Classification
    icp_matches = Column(JSON, default=[])  # List of matching ICP profile IDs
    role_type = Column(String, nullable=True)  # "first_marketer", "agency_replacement", etc.
    pain_tags = Column(JSON, default=[])  # "lead_gen", "brand", "chaos_culture", etc.

    # SPIN / MEDDIC-lite fields
    situation = Column(Text, nullable=True)
    problem = Column(Text, nullable=True)
    implication = Column(Text, nullable=True)
    need_payoff = Column(Text, nullable=True)
    economic_buyer_guess = Column(String, nullable=True)
    key_pain = Column(Text, nullable=True)
    chaos_flags = Column(JSON, default=[])
    silver_bullet_phrases = Column(JSON, default=[])

    # Deep context (generated by 4B model)
    context_dossier = Column(Text, nullable=True)
    challenger_insight = Column(Text, nullable=True)
    reframe_suggestion = Column(Text, nullable=True)

    # Enhanced intelligence fields (JSON for flexible storage)
    hidden_motivations = Column(JSON, nullable=True)
    competitive_threats = Column(JSON, nullable=True)
    psychological_profile = Column(JSON, nullable=True)
    attack_strategy = Column(JSON, nullable=True)
    unique_intelligence = Column(JSON, nullable=True)

    # Social media and research data
    social_profiles = Column(JSON, nullable=True)  # LinkedIn, Twitter data
    news_mentions = Column(JSON, nullable=True)   # Recent news/articles
    tech_stack = Column(JSON, nullable=True)      # Technology stack analysis

    # Status
    status = Column(String, default="new")  # "new", "contacted", "qualified", "pitched", "trial", "won", "lost", "parked"
    owner = Column(String, nullable=True)  # Who's working this lead
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="leads")
    contact = relationship("Contact", back_populates="leads")
    activities = relationship("Activity", back_populates="lead")
    outreach_logs = relationship("OutreachLog", back_populates="lead")
    signals = relationship("Signal", back_populates="lead")

class Activity(Base):
    """Activity log per lead (calls, messages, notes, tasks)."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    type = Column(String)  # "call", "email", "whatsapp", "note", "task"
    content = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="activities")

class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    outreach_type = Column(String, nullable=False)
    message_sent = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    response_received = Column(Boolean, default=False)
    response_text = Column(Text, nullable=True)

    lead = relationship("Lead", back_populates="outreach_logs")

class ScrapeSchedule(Base):
    """Configuration for scheduled scraping jobs."""
    __tablename__ = "scrape_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    # Schedule definition
    schedule_type = Column(String, default="interval")  # "cron" or "interval"
    cron_expression = Column(String, nullable=True)     # e.g. "0 9 * * *" (for cron)
    interval_minutes = Column(Integer, nullable=True)   # e.g. 1440 (24h) (for interval)
    
    # Job definition
    job_type = Column(String, nullable=False)  # "job_boards", "startup_listings", "custom_urls"
    job_params = Column(JSON, default={})      # e.g. {"query": "marketing", "sources": ["indeed"]}
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db(engine):
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def _normalize_key(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return " ".join(value.lower().split())


def _normalize_url(url):
    if url is None:
        return None
    url = url.strip().lower()
    if not url:
        return None
    if url.startswith("https://"):
        url = url[len("https://"):]
    elif url.startswith("http://"):
        url = url[len("http://"):]
    if url.startswith("www."):
        url = url[len("www."):]
    return url.rstrip("/")


def _website_candidates(website):
    raw = _normalize_key(website)
    if not raw:
        return []

    raw = raw.rstrip("/")
    candidates = {raw}

    no_scheme = _normalize_url(website)
    if no_scheme:
        candidates.add(no_scheme)
        candidates.add(f"https://{no_scheme}")
        candidates.add(f"http://{no_scheme}")
        candidates.add(f"www.{no_scheme}")
        candidates.add(f"https://www.{no_scheme}")
        candidates.add(f"http://www.{no_scheme}")

    return list(candidates)


def _extract_social_urls(social_links):
    if not social_links:
        return []

    if isinstance(social_links, list):
        items = social_links
    elif isinstance(social_links, dict):
        items = list(social_links.values())
    else:
        items = [social_links]

    urls = []
    for item in items:
        if not item:
            continue
        if isinstance(item, str):
            urls.append(item)
            continue
        if isinstance(item, dict):
            for v in item.values():
                if v:
                    urls.append(str(v))
            continue
        urls.append(str(item))

    return urls


def find_duplicate_lead(
    db,
    *,
    email=None,
    linkedin_url=None,
    contact_name=None,
    company_name=None,
    company_website=None,
):
    normalized_email = _normalize_key(email)
    normalized_linkedin = _normalize_url(linkedin_url)

    contact = None
    if normalized_email:
        contact = db.query(Contact).filter(func.lower(Contact.email) == normalized_email).first()

    company = None
    for candidate_website in _website_candidates(company_website):
        company = db.query(Company).filter(func.lower(Company.website) == candidate_website).first()
        if company:
            break

    normalized_company_name = _normalize_key(company_name)
    if company is None and normalized_company_name:
        company = db.query(Company).filter(func.lower(Company.name) == normalized_company_name).first()

    if contact is None and normalized_linkedin:
        query = db.query(Contact)
        if company is not None:
            query = query.filter(Contact.company_id == company.id)

        for candidate in query.all():
            candidate_urls = _extract_social_urls(candidate.social_links)
            if any(_normalize_url(u) == normalized_linkedin for u in candidate_urls):
                contact = candidate
                break

    normalized_contact_name = _normalize_key(contact_name)
    if contact is None and company is not None and normalized_contact_name:
        contact = (
            db.query(Contact)
            .filter(Contact.company_id == company.id)
            .filter(func.lower(Contact.name) == normalized_contact_name)
            .first()
        )

    if contact is None:
        return None

    return (
        db.query(Lead)
        .filter(Lead.contact_id == contact.id)
        .order_by(Lead.created_at.desc())
        .first()
    )
