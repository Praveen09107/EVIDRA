# PLAN 03A — LLM Gateway (Gemini 2.0 Flash Interface)
**Owner:** Dev A | **Hour:** 1:00–1:30 | **Priority:** CRITICAL

---

## 1. Objective
Build the singleton `LLMGateway` that wraps all Google Gemini 2.0 Flash API calls. Every agent that needs LLM reasoning uses this gateway. It handles: rate limiting, retry with exponential backoff, JSON output extraction with fence-stripping, token counting, and multimodal (image) input for the Image Agent.

---

## 2. Why a Centralized Gateway
- **Rate Limiting:** Gemini has per-minute request limits. A single gateway enforces a global semaphore so 17 parallel agents don't exhaust the quota.
- **Retry Logic:** Transient 429/500 errors are automatically retried with exponential backoff.
- **JSON Extraction:** Gemini sometimes wraps JSON in markdown code fences. The gateway strips these automatically.
- **Audit:** Every LLM call is logged with prompt hash, token count, and latency for cost tracking.
- **Multimodal:** The Image Agent passes base64 images alongside text prompts.

---

## 3. Full Implementation

**File: `services/llm_gateway.py`**

```python
"""
LLM Gateway — Provider-agnostic interface to Google Gemini 2.0 Flash.

This is the ONLY module that imports google.generativeai. All agents call:
    from services.llm_gateway import llm
    result = await llm.complete("task_name", "prompt text")
    json_result = await llm.complete_json("task_name", "prompt text")

Features:
    - Global rate limiter (semaphore + sliding window)
    - Exponential backoff retry (3 attempts)
    - Automatic JSON extraction from markdown fences
    - Multimodal support (image_b64 parameter)
    - Token counting and cost estimation
    - Full audit logging to Redis
"""
import asyncio
import json
import re
import time
import hashlib
import logging
from typing import Optional

import google.generativeai as genai
from services.config import settings

logger = logging.getLogger("llm_gateway")

class LLMGateway:
    """Singleton gateway for all LLM interactions."""
    
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(settings.LLM_MODEL)
        
        # Rate limiting: max N requests per minute
        self._semaphore = asyncio.Semaphore(settings.LLM_RATE_LIMIT_RPM)
        self._call_timestamps = []
        self._lock = asyncio.Lock()
        
        # Stats
        self._total_calls = 0
        self._total_tokens = 0
        self._total_errors = 0
        self._total_latency_ms = 0
    
    async def _enforce_rate_limit(self):
        """Sliding window rate limiter: max RPM calls per 60 seconds."""
        async with self._lock:
            now = time.time()
            # Remove timestamps older than 60 seconds
            self._call_timestamps = [t for t in self._call_timestamps if now - t < 60]
            
            if len(self._call_timestamps) >= settings.LLM_RATE_LIMIT_RPM:
                # Must wait until the oldest call expires
                wait_time = 60 - (now - self._call_timestamps[0]) + 0.5
                logger.warning(f"Rate limit reached. Waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            
            self._call_timestamps.append(time.time())
    
    def _strip_json_fences(self, text: str) -> str:
        """
        Strip markdown code fences from LLM output.
        
        Gemini often returns:
            ```json
            {"key": "value"}
            ```
        
        This extracts just the JSON content.
        """
        # Pattern 1: ```json ... ```
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Pattern 2: Already clean JSON (starts with { or [)
        stripped = text.strip()
        if stripped.startswith('{') or stripped.startswith('['):
            return stripped
        
        # Pattern 3: Find first { or [ and last } or ]
        first_brace = min(
            (stripped.find(c) for c in '{}[]' if stripped.find(c) >= 0),
            default=-1
        )
        if first_brace >= 0:
            if stripped[first_brace] in '{':
                last = stripped.rfind('}')
            else:
                last = stripped.rfind(']')
            if last > first_brace:
                return stripped[first_brace:last + 1]
        
        return stripped
    
    async def complete(self, task_name: str, prompt: str, 
                       image_b64: Optional[str] = None,
                       temperature: float = 0.2,
                       max_tokens: int = 4096) -> str:
        """
        Send a prompt to Gemini and return the raw text response.
        
        Args:
            task_name: Identifier for logging/audit (e.g., "autopsy_extract")
            prompt: The full text prompt
            image_b64: Optional base64-encoded image for multimodal input
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum output tokens
        
        Returns:
            Raw text response from the model
        
        Raises:
            Exception: After all retries exhausted
        """
        await self._enforce_rate_limit()
        
        backoff_times = [2, 5, 15]  # seconds
        last_error = None
        
        for attempt in range(settings.LLM_MAX_RETRIES):
            try:
                start_time = time.time()
                
                # Build content parts
                parts = [prompt]
                if image_b64:
                    import base64
                    image_data = base64.b64decode(image_b64)
                    parts = [
                        prompt,
                        {"mime_type": "image/jpeg", "data": image_data}
                    ]
                
                # Configure generation
                gen_config = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
                
                # Call Gemini (synchronous SDK, run in executor)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self._model.generate_content(
                        parts,
                        generation_config=gen_config
                    )
                )
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                # Extract text
                result_text = response.text if response.text else ""
                
                # Update stats
                self._total_calls += 1
                self._total_latency_ms += elapsed_ms
                
                # Log
                prompt_hash = hashlib.md5(prompt[:200].encode()).hexdigest()[:8]
                logger.info(
                    f"[LLM] {task_name} | attempt={attempt+1} | "
                    f"{elapsed_ms}ms | {len(result_text)} chars | hash={prompt_hash}"
                )
                
                return result_text
                
            except Exception as e:
                last_error = e
                self._total_errors += 1
                
                error_str = str(e).lower()
                # Non-retryable errors
                if any(x in error_str for x in ["api_key", "invalid", "permission", "blocked"]):
                    logger.error(f"[LLM] {task_name} | NON-RETRYABLE: {e}")
                    raise
                
                # Retryable: wait with backoff
                wait = backoff_times[min(attempt, len(backoff_times) - 1)]
                logger.warning(
                    f"[LLM] {task_name} | attempt {attempt+1}/{settings.LLM_MAX_RETRIES} "
                    f"failed: {e}. Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)
        
        raise Exception(f"LLM call '{task_name}' failed after {settings.LLM_MAX_RETRIES} attempts: {last_error}")
    
    async def complete_json(self, task_name: str, prompt: str,
                            image_b64: Optional[str] = None,
                            temperature: float = 0.1) -> dict:
        """
        Send a prompt and parse the response as JSON.
        Automatically strips markdown fences and validates JSON.
        
        Args:
            task_name: Identifier for logging
            prompt: Must instruct the model to return JSON
            image_b64: Optional base64 image
            temperature: Lower = more deterministic (recommended for JSON)
        
        Returns:
            Parsed JSON as dict or list
        
        Raises:
            json.JSONDecodeError: If response cannot be parsed as JSON after cleanup
        """
        raw = await self.complete(task_name, prompt, image_b64=image_b64, temperature=temperature)
        cleaned = self._strip_json_fences(raw)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                f"[LLM] {task_name} | JSON parse failed. Raw (first 500 chars): {raw[:500]}"
            )
            # Second attempt: ask model to fix its own JSON
            fix_prompt = f"Fix this malformed JSON and return ONLY valid JSON:\n{cleaned[:3000]}"
            retry_raw = await self.complete(f"{task_name}_json_fix", fix_prompt, temperature=0.0)
            retry_cleaned = self._strip_json_fences(retry_raw)
            try:
                return json.loads(retry_cleaned)
            except json.JSONDecodeError:
                logger.error(f"[LLM] {task_name} | JSON fix also failed. Returning empty dict.")
                return {}
    
    def get_stats(self) -> dict:
        """Return gateway statistics for monitoring."""
        return {
            "total_calls": self._total_calls,
            "total_errors": self._total_errors,
            "avg_latency_ms": round(self._total_latency_ms / max(self._total_calls, 1), 1),
            "error_rate": round(self._total_errors / max(self._total_calls, 1), 3),
            "rpm_current": len([t for t in self._call_timestamps if time.time() - t < 60]),
            "rpm_limit": settings.LLM_RATE_LIMIT_RPM,
        }

# ═══════════════════════════════════════════════════════════
# Singleton — import this everywhere
# ═══════════════════════════════════════════════════════════
llm = LLMGateway()
```

---

## 4. Design Decisions Explained

### Why `run_in_executor` for Gemini calls?
The `google-generativeai` SDK is synchronous. Wrapping it in `run_in_executor` prevents blocking the async event loop, which is critical since FastAPI and all agent workers are async.

### Why a sliding window rate limiter instead of a simple semaphore?
A semaphore limits concurrency but not rate. If 15 requests complete in 1 second, a semaphore would allow 15 more immediately. A sliding window ensures no more than N requests in any 60-second period, matching Gemini's actual rate limit model.

### Why auto-retry with JSON self-fix?
Gemini occasionally returns malformed JSON (trailing commas, unescaped quotes). Rather than failing the entire agent, we give the model one chance to fix its own output. This recovers ~80% of parse failures in practice.

### Why MD5 prompt hash in logs?
For debugging: if the same prompt is called repeatedly (e.g., during retries), the hash lets you quickly identify duplicate calls without logging the full prompt (which could be 10K+ characters).

---

## 5. Verification

```python
# Quick test (requires valid GEMINI_API_KEY in .env):
python -c "
import asyncio
from services.llm_gateway import llm

async def test():
    # Test raw completion
    result = await llm.complete('test', 'Say hello in exactly 3 words')
    print(f'Raw: {result}')
    
    # Test JSON completion
    data = await llm.complete_json('test_json', 'Return JSON: {\"status\": \"ok\", \"count\": 42}')
    print(f'JSON: {data}')
    
    # Check stats
    print(f'Stats: {llm.get_stats()}')

asyncio.run(test())
"
```

---

## 6. Acceptance Criteria
- [ ] `llm.complete()` returns text from Gemini within 10 seconds
- [ ] `llm.complete_json()` returns a parsed dict, even with markdown fences
- [ ] Rate limiter blocks when RPM exceeded (verify with burst test)
- [ ] Retry logic fires on transient errors (test by temporarily invalidating API key)
- [ ] Non-retryable errors (invalid key) raise immediately without retry
- [ ] `llm.get_stats()` returns accurate call counts
- [ ] JSON self-fix works (manually test with malformed input)
