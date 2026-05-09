"""
EVIDRA — LLM Gateway (Gemini 2.0 Flash).

All agents call the LLM through this gateway. Never call the Gemini API directly.
Features:
  - Async semaphore for concurrency limiting
  - Token tracking per pipeline run
  - Automatic retry with exponential backoff
  - Task-specific model configs (temperature, max_tokens)

Usage:
    from core.llm_gateway import llm

    response = await llm.complete(
        task="autopsy_extract",
        prompt="Extract structured fields from this autopsy report...",
        system_prompt="You are a forensic pathology expert."
    )
    print(response.text)
    print(response.tokens_used)
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional
import google.generativeai as genai
from core.config import settings

logger = logging.getLogger("evidra.llm")

# ═══════════════════════════════════════════════════════════
# Task-Specific Model Configurations
# ═══════════════════════════════════════════════════════════

TASK_MODEL_MAP = {
    "autopsy_extract":      {"temperature": 0.1, "max_output_tokens": 4000},
    "claim_extract":        {"temperature": 0.1, "max_output_tokens": 3000},
    "nli_classify":         {"temperature": 0.0, "max_output_tokens": 500},
    "hypothesis_reason":    {"temperature": 0.2, "max_output_tokens": 2000},
    "narrative_generate":   {"temperature": 0.3, "max_output_tokens": 1500},
    "hotspot_explain":      {"temperature": 0.2, "max_output_tokens": 800},
    "bias_assess":          {"temperature": 0.1, "max_output_tokens": 1000},
    "replay_narrative":     {"temperature": 0.3, "max_output_tokens": 800},
    "financial_classify":   {"temperature": 0.1, "max_output_tokens": 2000},
    "cdr_analyze":          {"temperature": 0.1, "max_output_tokens": 2000},
    "evidence_parse":       {"temperature": 0.0, "max_output_tokens": 2000},
    "nbe_suggest":          {"temperature": 0.2, "max_output_tokens": 1500},
    "general":              {"temperature": 0.2, "max_output_tokens": 2000},
}


@dataclass
class LLMResponse:
    """Structured response from the LLM Gateway."""
    text: str
    tokens_used: int
    model: str
    latency_ms: int
    task: str


class LLMGateway:
    """
    Centralized LLM Gateway. All agents use this.
    Thread-safe via asyncio.Semaphore for concurrency control.
    """

    def __init__(self):
        self._initialized = False
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._total_tokens_used = 0
        self._model_name = "gemini-2.0-flash"

    def _ensure_init(self):
        """Lazy initialization to avoid import-time API calls."""
        if not self._initialized:
            if not settings.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY not set — LLM calls will fail")
                return
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENT)
            self._initialized = True
            logger.info(f"LLM Gateway initialized (model={self._model_name}, max_concurrent={settings.LLM_MAX_CONCURRENT})")

    async def complete(
        self,
        task: str,
        prompt: str,
        system_prompt: str = "",
        **overrides
    ) -> LLMResponse:
        """
        Send a prompt to Gemini and return a structured response.

        Args:
            task:          Task key from TASK_MODEL_MAP (e.g. "autopsy_extract")
            prompt:        The user prompt / data to analyze
            system_prompt: System instruction for the model
            **overrides:   Override temperature, max_output_tokens, etc.
        """
        self._ensure_init()

        # Get task-specific config with overrides
        config = {**TASK_MODEL_MAP.get(task, TASK_MODEL_MAP["general"]), **overrides}

        # Token budget check
        if self._total_tokens_used >= settings.LLM_MAX_TOKENS_PER_RUN:
            raise TokenBudgetExceededError(
                f"Token budget exhausted: {self._total_tokens_used}/{settings.LLM_MAX_TOKENS_PER_RUN}"
            )

        # Semaphore for concurrency control
        async with self._semaphore:
            return await self._call_with_retry(task, prompt, system_prompt, config)

    async def _call_with_retry(
        self, task: str, prompt: str, system_prompt: str, config: dict,
        max_retries: int = 3
    ) -> LLMResponse:
        """Call Gemini with exponential backoff retry."""
        last_error = None

        for attempt in range(max_retries):
            try:
                start = time.monotonic()

                model = genai.GenerativeModel(
                    model_name=self._model_name,
                    system_instruction=system_prompt if system_prompt else None,
                    generation_config=genai.GenerationConfig(
                        temperature=config.get("temperature", 0.2),
                        max_output_tokens=config.get("max_output_tokens", 2000),
                    )
                )

                # Run the blocking SDK call in a thread
                response = await asyncio.to_thread(
                    model.generate_content, prompt
                )

                latency_ms = int((time.monotonic() - start) * 1000)

                # Extract token count
                tokens = 0
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    tokens = getattr(response.usage_metadata, 'total_token_count', 0)
                self._total_tokens_used += tokens

                result_text = ""
                if response.candidates and response.candidates[0].content.parts:
                    result_text = response.candidates[0].content.parts[0].text

                logger.info(
                    f"LLM [{task}] → {tokens} tokens, {latency_ms}ms "
                    f"(total: {self._total_tokens_used}/{settings.LLM_MAX_TOKENS_PER_RUN})"
                )

                return LLMResponse(
                    text=result_text,
                    tokens_used=tokens,
                    model=self._model_name,
                    latency_ms=latency_ms,
                    task=task,
                )

            except Exception as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(f"LLM [{task}] attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

        raise LLMCallError(f"LLM [{task}] failed after {max_retries} retries: {last_error}")

    def reset_token_counter(self):
        """Reset token counter (call at start of each pipeline run)."""
        self._total_tokens_used = 0

    @property
    def tokens_used(self) -> int:
        return self._total_tokens_used


class LLMCallError(Exception):
    """Raised when all LLM retry attempts fail."""
    pass


class TokenBudgetExceededError(Exception):
    """Raised when the per-pipeline token budget is exhausted."""
    pass


# Singleton instance
llm = LLMGateway()
