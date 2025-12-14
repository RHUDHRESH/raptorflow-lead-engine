from __future__ import annotations

import re
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from database import Company, Contact, Lead, find_duplicate_lead
from event_bus import event_bus

try:
    import phonenumbers
except ImportError:  # pragma: no cover
    phonenumbers = None


_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def _is_valid_email(email: Optional[str]) -> bool:
    if not email:
        return False
    return bool(_EMAIL_RE.fullmatch(email.strip()))


def _normalize_phone(phone: Optional[str], default_region: str = "IN") -> Optional[str]:
    if not phone:
        return None
    raw = phone.strip()
    if not raw:
        return None

    if phonenumbers is None:
        digits = re.sub(r"\D+", "", raw)
        if len(digits) < 8:
            return None
        return digits

    try:
        parsed = phonenumbers.parse(raw, default_region)
    except Exception:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def _has_circumstances(lead_fields: Dict[str, Any]) -> bool:
    for key in ("situation", "problem", "implication", "need_payoff", "key_pain"):
        value = lead_fields.get(key)
        if isinstance(value, str) and value.strip():
            return True

    pain_tags = lead_fields.get("pain_tags")
    if isinstance(pain_tags, list) and any(str(tag).strip() for tag in pain_tags):
        return True

    return False


def _contact_has_verified_phone(contact: Optional[Contact]) -> bool:
    if not contact:
        return False
    phone_numbers = contact.phone_numbers or []
    if isinstance(phone_numbers, dict):
        values = list(phone_numbers.values())
    elif isinstance(phone_numbers, list):
        values = phone_numbers
    else:
        values = [phone_numbers]

    for value in values:
        if not isinstance(value, str):
            continue
        if _normalize_phone(value):
            return True
    return False


def _contact_is_actionable(contact: Optional[Contact]) -> bool:
    if not contact:
        return False
    has_email = _is_valid_email(contact.email)
    has_phone = _contact_has_verified_phone(contact)
    return bool(has_email or has_phone)


_ALLOWED_LEAD_FIELDS = {
    "score_icp_fit",
    "score_marketing_pain",
    "score_data_quality",
    "score_executive_level",
    "score_budget_potential",
    "total_score",
    "score_bucket",
    "icp_matches",
    "role_type",
    "pain_tags",
    "situation",
    "problem",
    "implication",
    "need_payoff",
    "economic_buyer_guess",
    "key_pain",
    "chaos_flags",
    "silver_bullet_phrases",
    "context_dossier",
    "challenger_insight",
    "reframe_suggestion",
    "status",
    "owner",
    "notes",
}


def upsert_lead(
    db: Session,
    *,
    company_name: str,
    company_website: Optional[str] = None,
    contact_name: Optional[str] = None,
    role: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    lead_fields: Optional[Dict[str, Any]] = None,
    update_existing: bool = False,
    require_contact: bool = True,
) -> Dict[str, Any]:
    company_name = (company_name or "").strip()
    company_website = (company_website or "").strip() or None
    contact_name = (contact_name or "").strip() or None
    role = (role or "").strip() or None
    email = (email or "").strip().lower() or None
    phone = (phone or "").strip() or None
    linkedin_url = (linkedin_url or "").strip() or None

    if not company_name:
        raise ValueError("company_name is required")

    normalized_phone = _normalize_phone(phone) if phone else None

    if not contact_name and email:
        try:
            local = email.split("@", 1)[0]
            local = re.sub(r"[._-]+", " ", local).strip()
            contact_name = local.title() if local else None
        except Exception:
            contact_name = None

    has_contact_identifier = bool(email or normalized_phone or linkedin_url or contact_name)
    # For strict mode we do not raise here; we skip lead creation later and still allow
    # company/signal pipelines to persist context.

    existing = None
    if has_contact_identifier:
        existing = find_duplicate_lead(
            db,
            email=email,
            linkedin_url=linkedin_url,
            contact_name=contact_name,
            company_name=company_name,
            company_website=company_website,
        )

    filtered_lead_fields: Dict[str, Any] = {}
    if lead_fields:
        filtered_lead_fields = {k: v for k, v in lead_fields.items() if k in _ALLOWED_LEAD_FIELDS}

    if existing:
        if require_contact:
            has_complete_contact = _contact_is_actionable(existing.contact)

            circumstances_view = {
                "situation": filtered_lead_fields.get("situation") or existing.situation,
                "problem": filtered_lead_fields.get("problem") or existing.problem,
                "implication": filtered_lead_fields.get("implication") or existing.implication,
                "need_payoff": filtered_lead_fields.get("need_payoff") or existing.need_payoff,
                "key_pain": filtered_lead_fields.get("key_pain") or existing.key_pain,
                "pain_tags": filtered_lead_fields.get("pain_tags") or existing.pain_tags,
            }

            if not has_complete_contact or not _has_circumstances(circumstances_view):
                return {
                    "status": "incomplete",
                    "lead": None,
                    "company": existing.company,
                    "contact": existing.contact,
                }

        status = "duplicate"
        if update_existing and filtered_lead_fields:
            new_score = filtered_lead_fields.get("total_score")
            if new_score is None:
                new_score = 0
            try:
                new_score_value = float(new_score)
            except Exception:
                new_score_value = 0

            old_score = existing.total_score or 0
            if new_score_value > old_score:
                for key, value in filtered_lead_fields.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                db.add(existing)
                status = "updated"

        return {
            "status": status,
            "lead": existing,
            "company": existing.company,
            "contact": existing.contact,
        }

    company = None
    if company_website:
        company = db.query(Company).filter(Company.website == company_website).first()
        if company is None:
            company = db.query(Company).filter(Company.website.ilike(company_website)).first()

    if company is None:
        company = db.query(Company).filter(Company.name.ilike(company_name)).first()

    if company is None:
        company = Company(name=company_name, website=company_website)
        db.add(company)
        db.flush()

    if existing is None and not has_contact_identifier:
        existing = (
            db.query(Lead)
            .filter(Lead.company_id == company.id)
            .order_by(Lead.created_at.desc())
            .first()
        )

    if existing:
        if require_contact:
            has_complete_contact = _contact_is_actionable(existing.contact)

            circumstances_view = {
                "situation": filtered_lead_fields.get("situation") or existing.situation,
                "problem": filtered_lead_fields.get("problem") or existing.problem,
                "implication": filtered_lead_fields.get("implication") or existing.implication,
                "need_payoff": filtered_lead_fields.get("need_payoff") or existing.need_payoff,
                "key_pain": filtered_lead_fields.get("key_pain") or existing.key_pain,
                "pain_tags": filtered_lead_fields.get("pain_tags") or existing.pain_tags,
            }

            if not has_complete_contact or not _has_circumstances(circumstances_view):
                return {
                    "status": "incomplete",
                    "lead": None,
                    "company": existing.company,
                    "contact": existing.contact,
                }

        status = "duplicate"
        if update_existing and filtered_lead_fields:
            new_score = filtered_lead_fields.get("total_score")
            if new_score is None:
                new_score = 0
            try:
                new_score_value = float(new_score)
            except Exception:
                new_score_value = 0

            old_score = existing.total_score or 0
            if new_score_value > old_score:
                for key, value in filtered_lead_fields.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                db.add(existing)
                status = "updated"

        return {
            "status": status,
            "lead": existing,
            "company": existing.company,
            "contact": existing.contact,
        }

    contact = None
    if has_contact_identifier:
        if email:
            contact = db.query(Contact).filter(Contact.email.ilike(email)).first()

        if contact is None and contact_name:
            contact = (
                db.query(Contact)
                .filter(Contact.company_id == company.id)
                .filter(Contact.name.ilike(contact_name))
                .first()
            )

        if contact is None and linkedin_url:
            candidates = db.query(Contact).filter(Contact.company_id == company.id).all()
            for candidate in candidates:
                social_links = candidate.social_links or []
                if isinstance(social_links, dict):
                    social_values = list(social_links.values())
                elif isinstance(social_links, list):
                    social_values = social_links
                else:
                    social_values = [social_links]
                if any((isinstance(v, str) and v.strip() == linkedin_url) for v in social_values if v):
                    contact = candidate
                    break

        if contact is None:
            if require_contact and not (_is_valid_email(email) or normalized_phone):
                return {
                    "status": "incomplete",
                    "lead": None,
                    "company": company,
                    "contact": None,
                }

            social_links = []
            if linkedin_url:
                social_links.append(linkedin_url)
            contact = Contact(
                company_id=company.id,
                name=contact_name or "Website Contact",
                role=role,
                email=email,
                phone_numbers=[normalized_phone] if normalized_phone else [],
                social_links=social_links,
            )
            db.add(contact)
            db.flush()
        else:
            changed = False
            if contact_name and not contact.name:
                contact.name = contact_name
                changed = True
            if role and not contact.role:
                contact.role = role
                changed = True
            if normalized_phone:
                phone_numbers = contact.phone_numbers or []
                if isinstance(phone_numbers, dict):
                    phone_numbers = list(phone_numbers.values())
                elif not isinstance(phone_numbers, list):
                    phone_numbers = [phone_numbers]
                if normalized_phone not in phone_numbers:
                    phone_numbers.append(normalized_phone)
                    contact.phone_numbers = phone_numbers
                    changed = True
            if linkedin_url:
                social_links = contact.social_links or []
                if isinstance(social_links, dict):
                    social_links = list(social_links.values())
                elif not isinstance(social_links, list):
                    social_links = [social_links]
                if linkedin_url not in social_links:
                    social_links.append(linkedin_url)
                    contact.social_links = social_links
                    changed = True
            if changed:
                db.add(contact)

    if require_contact:
        has_complete_contact = _contact_is_actionable(contact)

        if not has_complete_contact or not _has_circumstances(filtered_lead_fields):
            return {
                "status": "incomplete",
                "lead": None,
                "company": company,
                "contact": contact,
            }

    lead = Lead(company_id=company.id, contact_id=(contact.id if contact else None), status="new")
    for key, value in filtered_lead_fields.items():
        if hasattr(lead, key):
            setattr(lead, key, value)
    db.add(lead)
    db.flush()

    event_bus.publish_sync(
        {
            "type": "lead_created",
            "data": {
                "id": lead.id,
                "company": company.name,
                "company_website": company.website,
                "score": lead.total_score,
                "score_bucket": lead.score_bucket,
                "role_type": lead.role_type,
                "contact": {
                    "id": contact.id if contact else None,
                    "name": contact.name if contact else None,
                    "role": contact.role if contact else None,
                    "email": contact.email if contact else None,
                    "phone_numbers": (
                        list((contact.phone_numbers or {}).values())
                        if contact and isinstance(contact.phone_numbers, dict)
                        else (contact.phone_numbers if contact else [])
                    )
                    or [],
                },
                "circumstances": {
                    "situation": lead.situation,
                    "problem": lead.problem,
                    "implication": lead.implication,
                    "need_payoff": lead.need_payoff,
                    "key_pain": lead.key_pain,
                    "pain_tags": lead.pain_tags,
                },
            },
        }
    )

    return {
        "status": "created",
        "lead": lead,
        "company": company,
        "contact": contact,
    }
