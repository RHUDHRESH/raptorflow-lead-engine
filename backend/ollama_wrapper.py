"""Ollama wrapper for 1B and 4B models."""

import json
import asyncio
import httpx
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Settings
from cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

class OllamaManager:
    """Manages Ollama model interactions (1B for routing, 4B for dossiers)."""

    def __init__(self):
        self.settings = Settings()
        self.base_url = self.settings.ollama_base_url
        
        # Select models based on quantization setting
        if self.settings.use_quantized_models:
            self.model_1b = self.settings.quantized_model_1b
            self.model_4b = self.settings.quantized_model_4b
            logger.info(f"Using quantized models: {self.model_1b}, {self.model_4b}")
        else:
            self.model_1b = self.settings.ollama_model_1b
            self.model_4b = self.settings.ollama_model_4b
            
        # Timeout: connection=10s, read=300s (for long model generation)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0))
        self.cache_manager = get_cache_manager()

    async def warm_up_models(self):
        """Warm up models in background to eliminate cold-start latency."""
        if not self.settings.enable_health_monitoring:
            return
            
        try:
            # Warm up 1B model with a simple prompt
            warmup_prompt = "Warm up: hello"
            await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_1b,
                    "prompt": warmup_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "max_tokens": 5,
                        **self._get_gpu_options()
                    }
                },
                timeout=10.0
            )
            logger.info("✅ 1B model warmed up")
            
            # Warm up 4B model if it's likely to be used
            if self.settings.classifier_score_threshold > 0:
                await self.client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_4b,
                        "prompt": warmup_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "max_tokens": 5,
                            **self._get_gpu_options()
                        }
                    },
                    timeout=15.0
                )
                logger.info("✅ 4B model warmed up")
                
        except Exception as e:
            logger.warning(f"Model warm-up failed (non-critical): {e}")

    async def start_background_warmup(self):
        """Start background model warm-up task."""
        if not self.settings.enable_health_monitoring:
            return
            
        try:
            # Run warm-up in background
            asyncio.create_task(self._background_warmup_loop())
        except Exception as e:
            logger.error(f"Failed to start background warmup: {e}")

    async def _background_warmup_loop(self):
        """Background loop to keep models warm."""
        while True:
            try:
                await asyncio.sleep(300)  # Warm up every 5 minutes
                await self.warm_up_models()
            except Exception as e:
                logger.warning(f"Background warmup failed: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def ensure_models_loaded(self):
        """Ensure optimal models are available, prioritizing quantized versions for performance."""
        try:
            models = await self._list_models()
            model_names = [m["name"] for m in models]
            
            # Check quantized models first if enabled
            if self.settings.use_quantized_models:
                quantized_1b_available = self.settings.quantized_model_1b in model_names
                quantized_4b_available = self.settings.quantized_model_4b in model_names
                
                if quantized_1b_available and quantized_4b_available:
                    self.model_1b = self.settings.quantized_model_1b
                    self.model_4b = self.settings.quantized_model_4b
                    logger.info(f"✅ Using quantized models: {self.model_1b}, {self.model_4b}")
                    return
                else:
                    # Fallback to full models if quantized not available
                    logger.warning("Quantized models not available, falling back to full models")
                    if not quantized_1b_available:
                        logger.warning(f"Quantized 1B model {self.settings.quantized_model_1b} not found")
                    if not quantized_4b_available:
                        logger.warning(f"Quantized 4B model {self.settings.quantized_model_4b} not found")
            
            # Use full models (either by config or fallback)
            self.model_1b = self.settings.ollama_model_1b
            self.model_4b = self.settings.ollama_model_4b
            
            # Ensure full models are available
            models_to_check = []
            if self.model_1b not in model_names:
                models_to_check.append(self.model_1b)
            if self.model_4b not in model_names:
                models_to_check.append(self.model_4b)
            
            for model_name in models_to_check:
                logger.warning(f"Model {model_name} not found. Pulling...")
                await self._pull_model(model_name)
            
            logger.info(f"✅ Models ready: {self.model_1b}, {self.model_4b}")
            
            # Start background warm-up if monitoring enabled
            await self.start_background_warmup()
            
        except Exception as e:
            logger.error(f"Error ensuring models are loaded: {e}")
            # Don't raise if we can continue with basic functionality
            logger.warning("Continuing with basic API functionality - AI features disabled")
            self.model_1b = None
            self.model_4b = None

    async def _list_models(self) -> list:
        """List available models in Ollama."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

    async def _pull_model(self, model_name: str):
        """Pull a model from Ollama."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=None,
            )
            response.raise_for_status()
            logger.info(f"✅ Model {model_name} pulled successfully")
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True
    )
    async def classify_signal(
        self,
        signal_text: str,
        icp_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Use Gemma 3 1B to quickly classify a signal.
        Returns structured JSON with ICP match, pain score, tags, SPIN/MEDDIC fields.
        """
        # Check cache
        if self.cache_manager:
            cached = await self.cache_manager.get(signal_text, str(icp_context), self.model_1b)
            if cached:
                return cached

        # Build classifier prompt
        icp_info = ""
        if icp_context:
            icp_info = f"""
ICP Context:
- Size buckets: {icp_context.get('size_buckets', [])}
- Industries: {icp_context.get('industries', [])}
- Pain keywords: {icp_context.get('pain_keywords', [])}
- Hiring keywords: {icp_context.get('hiring_keywords', [])}
"""

        prompt = f"""You are an elite lead qualification AI for enterprise sales teams. Focus on HIGH-VALUE targets only.

QUALIFICATION CRITERIA:
- Target: Founders, CEOs, CTOs, CMOs, VPs, Directors, Heads of Marketing
- Company Size: 10+ employees (ignore solo operators and tiny teams)
- Focus: Decision-makers with real pain and budget authority
- Avoid: Junior roles, individual contributors, entry-level hiring

{icp_info}

Signal Analysis:
{signal_text}

Return STRICT JSON:
{{
    "icp_match": true/false,
    "decision_making_level": "founder_ceo" or "c_level" or "vp_director" or "manager" or "individual" or "unknown",
    "company_size_estimate": "startup_1_10" or "small_11_50" or "medium_51_200" or "large_200_plus" or "enterprise_1000_plus",
    "budget_authority": "high_yes" or "medium_maybe" or "low_no",
    "role_type": "marketing_leader" or "founder_ceo" or "cto_tech" or "sales_director" or "agency_replacement" or "unclear",
    "target_priority": "strategic_gold" or "high_value" or "medium_potential" or "low_pass",
    "pain_tags": ["list", "critical", "pain", "points"],
    "score_fit": 0-50,
    "score_pain": 0-40,
    "score_data_quality": 0-10,
    "score_executive_level": 0-30,
    "score_budget_potential": 0-20,
    "reason_short": "max 25 words why this is/isn't a high-value target",
    "situation": "max 40 words",
    "problem": "max 40 words",
    "implication": "max 40 words",
    "need_payoff": "max 40 words",
    "economic_buyer_guess": "founder or ceo or cmo or cto or vp or director or gm or other",
    "key_pain": "max 40 words",
    "chaos_flags": ["list", "of", "flags"],
    "silver_bullet_phrases": ["list", "of", "phrases"],
    "urgency_level": "immediate_crisis" or "quarterly_priority" or "future_plan" or "nice_to_have"
}}"""

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_1b,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for consistent JSON
                        "top_p": 0.9,
                        "top_k": 40,
                        "num_ctx": 4096,  # Keep context small for 1B
                        **self._get_gpu_options()  # Add GPU acceleration if enabled
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            response_text = data.get("response", "").strip()

            # Try to extract JSON from response
            try:
                # Try direct JSON parse
                result = json.loads(response_text)
            except json.JSONDecodeError as parse_err:
                # Try to find JSON in the response
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    try:
                        result = json.loads(response_text[start_idx:end_idx])
                    except json.JSONDecodeError as nested_err:
                        logger.error(f"🔴 1B Model response parsing failed: {nested_err}")
                        logger.error(f"   Response text: {response_text[:300]}")
                        logger.warning("Using default classification (score: 0) as fallback")
                        result = self._default_classification()
                else:
                    logger.error(f"🔴 No JSON found in 1B model response")
                    logger.error(f"   Response: {response_text[:300]}")
                    logger.warning("Using default classification (score: 0) as fallback")
                    result = self._default_classification()

            # Cache the result
            if self.cache_manager:
                await self.cache_manager.set(signal_text, result, str(icp_context), self.model_1b)

            return result
        except httpx.TimeoutException as e:
            logger.error(f"🔴 TIMEOUT: 1B Model took too long to respond (>300s)")
            logger.error(f"   This usually means the model is overloaded or frozen")
            logger.warning("Returning default classification due to timeout")
            return self._default_classification()
        except httpx.ConnectError as e:
            logger.error(f"🔴 Connection lost to Ollama: {e}")
            logger.warning("Returning default classification due to connection error")
            return self._default_classification()
        except Exception as e:
            logger.error(f"🔴 Error in classify_signal: {type(e).__name__}: {e}")
            return self._default_classification()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True
    )
    async def generate_dossier(
        self,
        lead_json: Dict[str, Any],
        signal_snippets: list,
    ) -> Dict[str, str]:
        """
        Use Gemma 3 4B to generate rich context dossier for a hot lead.
        Only call this for leads scoring >70.
        """
        snippets_text = "\n".join([f"- {s}" for s in signal_snippets[:5]])  # Max 5 snippets

        prompt = f"""You are a world-class sales intelligence analyst with 15 years experience selling to marketing leaders.
You have access to proprietary lead intelligence that NO OTHER SALESPERSON has.

Analyze this lead data and generate DEEP, ACTIONABLE context using military-grade research techniques.
The goal: Give salespeople UNFAIR competitive advantage with insights competitors can't access.

Lead Data:
{json.dumps(lead_json, indent=2)}

Signal Snippets:
{snippets_text}

Return STRICT JSON with these fields (provide MAXIMUM unique intelligence):

{{
    "snapshot": "45 words exactly: who they are, business stage, monetization status, team size, pain urgency",
    "hidden_motivations": [
        "Their real reason for hiring (beyond obvious job description)",
        "What they're actually struggling with that they won't admit",
        "Their personality-driven pain (founder ego, team drama, investor pressure)"
    ],
    "competitive_threats": [
        "How competitors are already winning their business",
        "Their dead-end marketing strategies you're seeing signals of",
        "Why their current agency/employee is failing them"
    ],
    "psychological_profile": {{
        "decision_style": "autocratic/collaborative/risk-averse/adventurous",
        "pain_tolerance": "low/high/breaking_point",
        "trust_barriers": "What makes them skeptical of outsiders",
        "motivation_triggers": "What stories/values resonate with them"
    }},
    "uncomfortable_truth": "2 sentences maximum: the brutal reality they need to face that no one tells them",
    "reframe_suggestion": "1 killer sentence that completely flips their worldview and positions you as the obvious solution",
    "attack_strategy": {{
        "opening_sequence": "How to create immediate rapport and credibility",
        "value_stacking": ["3 specific outcomes they get day 1, week 1, month 1"],
        "objection_preemption": ["The 2 objections they'll raise and how to disarm them"],
        "closing_signals": ["4 behaviors indicating they're ready to buy"]
    }},
    "challenger_insight": "The ONE assumption they hold that's destroying their business - demolish it",
    "unique_intelligence": {{
        "market_signals": "What their job post reveals about market changes they're missing",
        "competitor_weakness": "How you can exploit gaps in their competitive landscape",
        "timing_opportunity": "Why NOW is the perfect moment to approach them"
    }}
}}"""

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_4b,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,  # Slightly higher for better narrative
                        "top_p": 0.9,
                        "num_ctx": 8192,  # 4B can handle more context
                        **self._get_gpu_options()  # Add GPU acceleration if enabled
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            response_text = data.get("response", "").strip()

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as parse_err:
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    try:
                        result = json.loads(response_text[start_idx:end_idx])
                    except json.JSONDecodeError as nested_err:
                        logger.error(f"🔴 4B Dossier response parsing failed: {nested_err}")
                        logger.error(f"   Response: {response_text[:300]}")
                        logger.warning("Using default dossier as fallback")
                        result = self._default_dossier()
                else:
                    logger.error(f"🔴 No JSON found in 4B dossier response")
                    logger.error(f"   Response: {response_text[:300]}")
                    logger.warning("Using default dossier as fallback")
                    result = self._default_dossier()

            return result
        except httpx.TimeoutException as e:
            logger.error(f"🔴 TIMEOUT: 4B Dossier model took too long (>300s)")
            logger.error(f"   This usually means the model is overloaded")
            logger.warning("Using default dossier (skipping enrichment)")
            return self._default_dossier()
        except httpx.ConnectError as e:
            logger.error(f"🔴 Connection lost to Ollama during dossier generation: {e}")
            logger.warning("Using default dossier")
            return self._default_dossier()
        except Exception as e:
            logger.error(f"🔴 Error generating dossier: {type(e).__name__}: {e}")
            logger.warning("Returning default dossier due to error")
            return self._default_dossier()

    async def classify_signal_streaming(
        self,
        signal_text: str,
        icp_context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream classification results in real-time."""
        if not self.settings.enable_streaming:
            # Fallback to non-streaming
            result = await self.classify_signal(signal_text, icp_context)
            yield result
            return

        # Build classifier prompt (same as non-streaming)
        icp_info = ""
        if icp_context:
            icp_info = f"""
ICP Context:
- Size buckets: {icp_context.get('size_buckets', [])}
- Industries: {icp_context.get('industries', [])}
- Pain keywords: {icp_context.get('pain_keywords', [])}
- Hiring keywords: {icp_context.get('hiring_keywords', [])}
"""

        prompt = f"""You are an elite lead qualification AI for enterprise sales teams. Focus on HIGH-VALUE targets only.

QUALIFICATION CRITERIA:
- Target: Founders, CEOs, CTOs, CMOs, VPs, Directors, Heads of Marketing
- Company Size: 10+ employees (ignore solo operators and tiny teams)
- Focus: Decision-makers with real pain and budget authority
- Avoid: Junior roles, individual contributors, entry-level hiring

{icp_info}

Signal Analysis:
{signal_text}

Return STRICT JSON:
{{
    "icp_match": true/false,
    "decision_making_level": "founder_ceo" or "c_level" or "vp_director" or "manager" or "individual" or "unknown",
    "company_size_estimate": "startup_1_10" or "small_11_50" or "medium_51_200" or "large_200_plus" or "enterprise_1000_plus",
    "budget_authority": "high_yes" or "medium_maybe" or "low_no",
    "role_type": "marketing_leader" or "founder_ceo" or "cto_tech" or "sales_director" or "agency_replacement" or "unclear",
    "target_priority": "strategic_gold" or "high_value" or "medium_potential" or "low_pass",
    "pain_tags": ["list", "critical", "pain", "points"],
    "score_fit": 0-50,
    "score_pain": 0-40,
    "score_data_quality": 0-10,
    "score_executive_level": 0-30,
    "score_budget_potential": 0-20,
    "reason_short": "max 25 words why this is/isn't a high-value target",
    "situation": "max 40 words",
    "problem": "max 40 words",
    "implication": "max 40 words",
    "need_payoff": "max 40 words",
    "economic_buyer_guess": "founder or ceo or cmo or cto or vp or director or gm or other",
    "key_pain": "max 40 words",
    "chaos_flags": ["list", "of", "flags"],
    "silver_bullet_phrases": ["list", "of", "phrases"],
    "urgency_level": "immediate_crisis" or "quarterly_priority" or "future_plan" or "nice_to_have"
}}"""

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_1b,
                        "prompt": prompt,
                        "stream": True,  # Enable streaming
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.9,
                            "top_k": 40,
                            "num_ctx": 4096,
                            **self._get_gpu_options()
                        }
                    },
                )
                
                response.raise_for_status()
                
                # Stream response
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("done", False):
                                break
                            if "response" in data:
                                yield {"chunk": data["response"], "done": False}
                        except json.JSONDecodeError:
                            continue
                
                # Final result
                yield {"done": True, "message": "Classification complete"}
                
        except Exception as e:
            logger.error(f"Streaming classification failed: {e}")
            yield {"error": str(e), "done": True}

    async def generate_dossier_streaming(
        self,
        lead_json: Dict[str, Any],
        signal_snippets: list,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream dossier generation in real-time."""
        if not self.settings.enable_streaming:
            # Fallback to non-streaming
            result = await self.generate_dossier(lead_json, signal_snippets)
            yield result
            return

        snippets_text = "\n".join([f"- {s}" for s in signal_snippets[:5]])
        prompt = f"""You are a world-class sales intelligence analyst with 15 years experience selling to marketing leaders.

Analyze this lead data and generate DEEP, ACTIONABLE context using military-grade research techniques.

Lead Data:
{json.dumps(lead_json, indent=2)}

Signal Snippets:
{snippets_text}

Return STRICT JSON with these fields..."""  # Truncated for brevity

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_4b,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": 0.5,
                            "top_p": 0.9,
                            "num_ctx": 8192,
                            **self._get_gpu_options()
                        }
                    },
                )
                
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("done", False):
                                break
                            if "response" in data:
                                yield {"chunk": data["response"], "done": False}
                        except json.JSONDecodeError:
                            continue
                
                yield {"done": True, "message": "Dossier generation complete"}
                
        except Exception as e:
            logger.error(f"Streaming dossier generation failed: {e}")
            yield {"error": str(e), "done": True}

    def _get_gpu_options(self) -> Dict[str, Any]:
        """Get GPU acceleration options if enabled in configuration."""
        if not self.settings.enable_gpu_acceleration:
            return {}
        
        gpu_options = {}
        
        # Set GPU backend
        if self.settings.gpu_backend != "auto":
            gpu_options["backend"] = self.settings.gpu_backend
        
        # Set device ID if specified
        if self.settings.gpu_device_id != 0:
            gpu_options["device"] = f"{self.settings.gpu_backend}:{self.settings.gpu_device_id}"
        
        # Set memory limit if specified
        if self.settings.gpu_memory_limit:
            gpu_options["gpu_memory_utilization"] = 0.9  # Use 90% of available memory
        
        # Set thread count
        if self.settings.gpu_threads > 1:
            gpu_options["num_thread"] = self.settings.gpu_threads
        
        # Set batch size for parallel processing
        if self.settings.gpu_batch_size > 1:
            gpu_options["batch_size"] = self.settings.gpu_batch_size
        
        logger.debug(f"Using GPU options: {gpu_options}")
        return gpu_options

    def _default_classification(self) -> Dict[str, Any]:
        """Default classification when model fails."""
        return {
            "icp_match": False,
            "size_bucket": "unknown",
            "region": "unknown",
            "role_type": "unclear",
            "pain_tags": [],
            "score_fit": 0,
            "score_pain": 0,
            "score_data_quality": 0,
            "reason_short": "Classification failed",
            "situation": "",
            "problem": "",
            "implication": "",
            "need_payoff": "",
            "economic_buyer_guess": "unknown",
            "key_pain": "",
            "chaos_flags": [],
            "silver_bullet_phrases": [],
        }

    def _default_dossier(self) -> Dict[str, Any]:
        """Default dossier when model fails."""
        return {
            "snapshot": "Lead context generation failed.",
            "why_pain_bullets": [],
            "uncomfortable_truth": "Unable to generate insight.",
            "reframe_suggestion": "Unable to generate reframe.",
            "best_angle_bullets": [],
            "challenger_insight": "Unable to generate insight.",
        }


def _compute_score_bucket(total_score: float) -> str:
    """Map numeric score to bucket labels."""
    if total_score >= 80:
        return "red_hot"
    if total_score >= 60:
        return "warm"
    if total_score >= 40:
        return "nurture"
    return "parked"


def classify_signal_with_ollama(
    signal_text: str,
    company_name: Optional[str] = None,
    company_website: Optional[str] = None,
    icp_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synchronous helper used by scraping pipelines to classify a signal via Ollama.

    This keeps the scraping service (which runs in sync contexts) working without
    needing an event loop. It mirrors the async classifier logic but uses the
    blocking httpx client.
    """
    settings = Settings()
    manager = OllamaManager()  # For defaults + model names
    icp_context = icp_context or {}
    cache_manager = get_cache_manager()

    # Check cache (sync)
    if cache_manager:
        cached = cache_manager.get_sync(signal_text, str(icp_context), manager.model_1b)
        if cached:
            # Ensure normalized score is present if cached raw result
            if "total_score" not in cached:
                 # Re-calculate derived fields if needed, or assume cached is the full normalized object
                 # The async set() stores the RAW result from Ollama (JSON) or the processed one?
                 # In async classify_signal, we store 'result' which is the parsed JSON from Ollama.
                 # We need to process it below to add total_score etc.
                 pass
            else:
                 return cached # If we cached the final result

    icp_info = ""
    if icp_context:
        icp_info = f"""
ICP Context:
- Size buckets: {icp_context.get('size_buckets', [])}
- Industries: {icp_context.get('industries', [])}
- Pain keywords: {icp_context.get('pain_keywords', [])}
- Hiring keywords: {icp_context.get('hiring_keywords', [])}
"""

    prompt = f"""You are an elite lead qualification AI for enterprise sales teams. Focus on HIGH-VALUE targets only.

QUALIFICATION CRITERIA:
- Target: Founders, CEOs, CTOs, CMOs, VPs, Directors, Heads of Marketing
- Company Size: 10+ employees (ignore solo operators and tiny teams)
- Focus: Decision-makers with real pain and budget authority
- Avoid: Junior roles, individual contributors, entry-level hiring

{icp_info}

Signal Analysis:
{signal_text}

Return STRICT JSON:
{{
    "icp_match": true/false,
    "decision_making_level": "founder_ceo" or "c_level" or "vp_director" or "manager" or "individual" or "unknown",
    "company_size_estimate": "startup_1_10" or "small_11_50" or "medium_51_200" or "large_200_plus" or "enterprise_1000_plus",
    "budget_authority": "high_yes" or "medium_maybe" or "low_no",
    "role_type": "marketing_leader" or "founder_ceo" or "cto_tech" or "sales_director" or "agency_replacement" or "unclear",
    "target_priority": "strategic_gold" or "high_value" or "medium_potential" or "low_pass",
    "pain_tags": ["list", "critical", "pain", "points"],
    "score_fit": 0-50,
    "score_pain": 0-40,
    "score_data_quality": 0-10,
    "score_executive_level": 0-30,
    "score_budget_potential": 0-20,
    "reason_short": "max 25 words why this is/isn't a high-value target",
    "situation": "max 40 words",
    "problem": "max 40 words",
    "implication": "max 40 words",
    "need_payoff": "max 40 words",
    "economic_buyer_guess": "founder or ceo or cmo or cto or vp or director or gm or other",
    "key_pain": "max 40 words",
    "chaos_flags": ["list", "of", "flags"],
    "silver_bullet_phrases": ["list", "of", "phrases"],
    "urgency_level": "immediate_crisis" or "quarterly_priority" or "future_plan" or "nice_to_have"
}}"""

    try:
        with httpx.Client(timeout=httpx.Timeout(10.0, read=300.0)) as client:
            response = client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": manager.model_1b,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": settings.temperature_1b,
                        "top_p": 0.9,
                        "top_k": 40,
                        "num_ctx": settings.context_window_1b_short,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            response_text = data.get("response", "").strip()

        try:
            classification = json.loads(response_text)
        except json.JSONDecodeError:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                classification = json.loads(response_text[start_idx:end_idx])
            else:
                logger.warning("Could not parse classification JSON; using default.")
                classification = manager._default_classification()
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Classification via Ollama failed: {exc}")
        classification = manager._default_classification()

    total_score = (
        classification.get("score_fit", 0)
        + classification.get("score_pain", 0)
        + classification.get("score_data_quality", 0)
    )
    score_bucket = _compute_score_bucket(total_score)

    # Normalize output to match Lead columns expected by scraping_service
    result = {
        "icp_match": classification.get("icp_match", False),
        "score_icp_fit": classification.get("score_fit", 0),
        "score_marketing_pain": classification.get("score_pain", 0),
        "score_data_quality": classification.get("score_data_quality", 0),
        "total_score": total_score,
        "score_bucket": score_bucket,
        "icp_matches": classification.get("icp_matches", []),
        "role_type": classification.get("role_type", "unclear"),
        "pain_tags": classification.get("pain_tags", []),
        "situation": classification.get("situation", ""),
        "problem": classification.get("problem", ""),
        "implication": classification.get("implication", ""),
        "need_payoff": classification.get("need_payoff", ""),
        "economic_buyer_guess": classification.get("economic_buyer_guess", "unknown"),
        "key_pain": classification.get("key_pain", ""),
        "chaos_flags": classification.get("chaos_flags", []),
        "silver_bullet_phrases": classification.get("silver_bullet_phrases", []),
        "status": "new",
    }

    # Cache the FINAL processed result
    if cache_manager:
        cache_manager.set_sync(signal_text, result, str(icp_context), manager.model_1b)

    return result


_ollama_manager: Optional[OllamaManager] = None


def get_ollama_manager() -> Optional[OllamaManager]:
    return _ollama_manager


def init_ollama_manager() -> OllamaManager:
    global _ollama_manager
    if _ollama_manager is None:
        _ollama_manager = OllamaManager()
    return _ollama_manager
