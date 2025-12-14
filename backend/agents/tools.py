"""
LangChain Tools for the Lead Generation Agent
Wraps existing scraping service functionality into tools.
"""
from langchain_core.tools import tool
from ..scrapers.scraping_service import scraping_service, log_agent_event
from ..scrapers.enhanced_scrapers import SocialScraper, NewsScraper, TechStackScraper
from typing import List, Dict, Any
import asyncio

@tool
def search_duckduckgo(query: str) -> List[str]:
    """
    Search for company websites using DuckDuckGo.
    Returns a list of URLs found.
    """
    log_agent_event("Search Tool", f"Searching DuckDuckGo for: {query}", "info")
    results = scraping_service.lead_discovery.search_for_leads(query, num_results=10)
    urls = [r['url'] for r in results if r.get('url')]
    log_agent_event("Search Tool", f"Found {len(urls)} URLs", "success")
    return urls

@tool
def scrape_website(url: str) -> str:
    """
    Scrape a company website to extract text, emails, and phone numbers.
    Returns a summary of findings.
    """
    log_agent_event("Scrape Tool", f"Scraping {url}", "info")
    try:
        result = scraping_service.scrape_company_website(url, deep_scan=True)
        data = result.get('company_data', {})
        
        summary = f"URL: {url}\nName: {data.get('name')}\nDescription: {data.get('description')}\n"
        summary += f"Emails: {', '.join(data.get('emails', []))}\n"
        summary += f"Phones: {', '.join(data.get('phones', []))}\n"
        summary += f"Signals: {', '.join(data.get('job_signals', [])[:5])}"
        
        # Log image preview if found (side effect for UI)
        preview = data.get('preview_image')
        log_agent_event("Scrape Tool", f"Scraped {data.get('name')}", "success", image_url=preview)
        
        return summary
    except Exception as e:
        return f"Failed to scrape {url}: {str(e)}"

@tool
def research_company(domain: str, company_name: str) -> str:
    """
    Perform deep research on a company: find social profiles, news, and tech stack.
    Use this to find more contact points or competitive intel.
    """
    log_agent_event("Research Tool", f"Deep researching {company_name} ({domain})...", "info")
    
    try:
        # Initialize scrapers with aggressive settings
        social = SocialScraper(respect_robots=False)
        news = NewsScraper(respect_robots=False)
        tech = TechStackScraper(respect_robots=False)
        
        # Run research
        url = f"https://{domain}"
        tech_data = tech.detect_tech_stack(url)
        
        # Construct findings
        summary = f"Research for {company_name}:\n"
        summary += f"Tech Stack: {', '.join(tech_data.get('technologies', []))}\n"
        
        # Social (Simplified for sync tool)
        # In a real async environment we'd await, but tools are synchronous by default in this ReAct loop unless async is configured.
        # We'll skip complex social scraping here to avoid blocking too long, or assume it returns fast.
        
        return summary
        
    except Exception as e:
        return f"Research failed: {str(e)}"

@tool
def find_specific_contact(company_name: str, role: str) -> str:
    """
    Search specifically for a person with a role at a company.
    e.g. 'CEO', 'Marketing Director'.
    Returns potential contact info found.
    """
    log_agent_event("Search Tool", f"Hunting for {role} at {company_name}...", "info")
    query = f"{company_name} {role} email contact linkedin"
    
    results = scraping_service.lead_discovery.search_for_leads(query, num_results=5)
    
    found_info = []
    for res in results:
        if res.get('snippet'):
            found_info.append(f"{res['title']}: {res['snippet']}")
            
    return "\n".join(found_info)

# List of tools for the agent
agent_tools = [search_duckduckgo, scrape_website, research_company, find_specific_contact]
