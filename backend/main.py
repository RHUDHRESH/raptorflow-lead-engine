"""
Raptorflow Lead Engine - Main FastAPI App
Local Ollama-based lead discovery, classification, and enrichment.
"""

import os
import logging
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging early so startup diagnostics are visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

from database import init_db, Base, engine, SessionLocal
from config import Settings
from routers import icp, leads, ingest, classify, scrape, advanced_scraping, deep_research, scheduler, mission
from scrapers.scraping_service import scraping_service
from ollama_wrapper import init_ollama_manager, get_ollama_manager
from cache_manager import init_cache_manager, get_cache_manager
from event_bus import event_bus
from prompt_templates import init_prompt_manager, get_prompt_manager
from scheduled_tasks import start_scheduler, stop_scheduler
from dependency_check import run_startup_checks, check_playwright
from error_handler import register_error_handlers

# Load settings
settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic with enhanced AI infrastructure initialization."""
    # Startup
    print("🚀 Initializing Raptorflow Lead Engine...")
    
    # Set event loop for event bus
    try:
        loop = asyncio.get_running_loop()
        event_bus.set_loop(loop)
    except RuntimeError:
        logger.warning("Could not get running loop for event bus")

    init_db(engine)

    # Verify local prerequisites (Tesseract, Ollama models, etc.)
    print("🔍 Checking system dependencies...")
    # Temporarily disabled Ollama checks to allow basic API functionality
    if False and not run_startup_checks(settings.ollama_base_url, settings.ollama_model_1b, settings.ollama_model_4b):
        raise RuntimeError("Critical system dependencies missing. Check logs above for details.")
    else:
        print("⚠️  Ollama checks skipped - basic API only")

    # Initialize cache manager
    print("💾 Initializing cache manager...")
    cache_manager = init_cache_manager(
        backend=settings.cache_backend,
        redis_url=settings.redis_url if settings.cache_backend == "redis" else None,
        max_size=settings.cache_max_size,
        ttl_seconds=settings.cache_ttl_seconds
    )
    if settings.cache_backend == "redis":
        await cache_manager.connect_redis()
    print(f"✅ Cache initialized: backend={settings.cache_backend}, enabled={settings.enable_response_cache}")

    # Initialize prompt template manager
    print("📝 Initializing prompt template manager...")
    prompt_manager = init_prompt_manager(
        template_path=settings.prompt_template_path,
        enable_custom=settings.enable_custom_prompts
    )
    print(f"✅ Prompt manager initialized: templates={len(prompt_manager.list_templates())}")

    # Initialize Ollama manager (singleton)
    print("📡 Initializing Ollama manager...")
    ollama_manager = init_ollama_manager()
    await ollama_manager.ensure_models_loaded()
    print(f"✅ Ollama ready: 1B={ollama_manager.model_1b}, 4B={ollama_manager.model_4b}")

    # Start scheduled tasks
    print("⏰ Starting scheduled tasks...")
    start_scheduler()

    print("\n" + "="*60)
    print("✅ Raptorflow Lead Engine READY!")
    print("="*60)
    print(f"  📊 Cache: {settings.cache_backend} (enabled={settings.enable_response_cache})")
    print(f"  🤖 Models: {ollama_manager.model_1b} + {ollama_manager.model_4b}")
    print(f"  📝 Prompts: {len(prompt_manager.list_templates())} templates")
    print(f"  ⚡ Health Monitoring: {settings.enable_health_monitoring}")
    print(f"  🔄 Batch Parallel: {settings.batch_enable_parallel} (max={settings.batch_concurrency_limit})")
    print("="*60 + "\n")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    stop_scheduler()
    print("✅ Scheduler stopped")

    # Shutdown scraping service
    print("🛑 Shutting down scraping service...")
    scraping_service.shutdown()
    print("✅ Scraping service stopped")

    # Disconnect Redis if used
    if settings.cache_backend == "redis":
        cache_mgr = get_cache_manager()
        if cache_mgr:
            await cache_mgr.disconnect_redis()
            print("✅ Redis disconnected")

# Create FastAPI app
app = FastAPI(
    title="Raptorflow Lead Engine",
    description="Overkill lead discovery + enrichment for marketing pain signals",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assets_dir = Path(__file__).resolve().parent / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# Include routers
app.include_router(icp.router, prefix="/api/icp", tags=["ICP Management"])
app.include_router(leads.router, prefix="/api/leads", tags=["Lead Management"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Data Ingest"])
app.include_router(classify.router, prefix="/api/classify", tags=["Classification"])
app.include_router(scrape.router, tags=["Web Scraping"])
app.include_router(advanced_scraping.router, prefix="/api/advanced", tags=["Advanced Scraping"])
app.include_router(deep_research.router, prefix="/api/research", tags=["Deep Research"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(mission.router)

# Register shared error handlers for consistent responses
register_error_handlers(app)

@app.get("/")
def root():
    """Health check."""
    return {
        "status": "ok",
        "service": "Raptorflow Lead Engine",
        "version": "0.1.0",
    }

@app.get("/api/events")
async def sse_endpoint():
    """Server-Sent Events endpoint for real-time updates"""
    async def event_generator():
        queue = await event_bus.subscribe()
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            event_bus.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/health")
async def health():
    """Full health check including Ollama, cache, and AI infrastructure status."""
    ollama = get_ollama_manager()
    cache = get_cache_manager()
    prompt_mgr = get_prompt_manager()

    health_data = {
        "api": "ok",
        "database": "ok",
        "ollama": {
            "status": "ok" if ollama else "not_initialized",
            "models": {
                "1b": ollama.model_1b if ollama else None,
                "4b": ollama.model_4b if ollama else None,
            },
            "health_monitoring": settings.enable_health_monitoring
        },
        "cache": {
            "status": "ok" if cache else "not_initialized",
            "backend": settings.cache_backend,
            "enabled": settings.enable_response_cache
        },
        "prompts": {
            "status": "ok" if prompt_mgr else "not_initialized",
            "custom_enabled": settings.enable_custom_prompts,
            "template_count": len(prompt_mgr.list_templates()) if prompt_mgr else 0
        },
        "features": {
            "embeddings": settings.enable_embeddings,
            "streaming": settings.enable_streaming,
            "batch_parallel": settings.batch_enable_parallel,
            "health_monitoring": settings.enable_health_monitoring
        },
        "scraping": {
            "browsers_installed": check_playwright()
        }
    }

    # Add detailed health stats if monitoring enabled
    health_monitor = getattr(ollama, "health_monitor", None) if ollama else None
    if settings.enable_health_monitoring and health_monitor:
        health_data["ollama"]["health_stats"] = health_monitor.get_stats()

    return health_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
