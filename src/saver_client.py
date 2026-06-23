import os
from typing import Any, Optional

from anthropic import Anthropic as OriginalAnthropic

from .cache import get_cached_response, cache_response
from .tracker import log_usage
from .compressor import compress_conversation, optimize_prompt, estimate_tokens


class SaverAnthropic:
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = OriginalAnthropic(api_key=self._api_key, **kwargs)
        self._cache_enabled = True
        self._compress_enabled = True
        self._optimize_enabled = True
        self._max_context_tokens = 4000
        self._stats = {"cache_hits": 0, "cache_misses": 0, "tokens_saved": 0, "cost_saved": 0.0}

    @property
    def messages(self):
        return _MessagesWrapper(self)

    def _make_messages_request(self, **kwargs):
        model = kwargs.get("model", "claude-3-sonnet-20240229")
        messages = kwargs.get("messages", [])
        system = kwargs.get("system", "")
        max_tokens = kwargs.get("max_tokens", 1024)
        temperature = kwargs.get("temperature", 1.0)

        prompt_text = system + "\n" + "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
        )

        if self._optimize_enabled:
            prompt_text = optimize_prompt(prompt_text)

        compressed = messages
        if self._compress_enabled:
            compressed = compress_conversation(messages, self._max_context_tokens)
        prompt_text_compressed = system + "\n" + "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in compressed
        )

        if self._cache_enabled:
            cached = get_cached_response(prompt_text_compressed, model)
            if cached:
                self._stats["cache_hits"] += 1
                tokens_saved = estimate_tokens(prompt_text_compressed)
                cost_saved = (tokens_saved / 1000) * 0.015
                self._stats["tokens_saved"] += tokens_saved
                self._stats["cost_saved"] += cost_saved
                log_usage(
                    model=model,
                    prompt_tokens=tokens_saved,
                    completion_tokens=0,
                    cached_tokens=tokens_saved,
                    prompt_preview=prompt_text[:80],
                )
                return _CachedResponse(cached)

        self._stats["cache_misses"] += 1

        kwargs_copy = dict(kwargs)
        kwargs_copy["model"] = model

        if self._compress_enabled and compressed != messages:
            kwargs_copy["messages"] = compressed

        response = self._client.messages.create(**kwargs_copy)

        if self._cache_enabled:
            response_text = ""
            if hasattr(response, "content") and response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        response_text += block.text
            if response_text:
                tokens_used = estimate_tokens(prompt_text_compressed)
                cache_response(prompt_text_compressed, response_text, model, tokens_used)

        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage"):
            prompt_tokens = response.usage.input_tokens if hasattr(response.usage, "input_tokens") else 0
            completion_tokens = response.usage.output_tokens if hasattr(response.usage, "output_tokens") else 0

        log_usage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_preview=prompt_text[:80],
        )

        return response

    def get_stats(self) -> dict:
        return dict(self._stats)

    def reset_stats(self):
        self._stats = {"cache_hits": 0, "cache_misses": 0, "tokens_saved": 0, "cost_saved": 0.0}

    def configure(self, cache: Optional[bool] = None, compress: Optional[bool] = None,
                  optimize: Optional[bool] = None, max_context_tokens: Optional[int] = None):
        if cache is not None:
            self._cache_enabled = cache
        if compress is not None:
            self._compress_enabled = compress
        if optimize is not None:
            self._optimize_enabled = optimize
        if max_context_tokens is not None:
            self._max_context_tokens = max_context_tokens


class _MessagesWrapper:
    def __init__(self, client: SaverAnthropic):
        self._client = client

    def create(self, **kwargs):
        return self._client._make_messages_request(**kwargs)


class _CachedResponse:
    def __init__(self, text: str):
        self.content = [_CachedContentBlock(text)]
        self.usage = _CachedUsage()
        self.stop_reason = "end_turn"
        self.stop_sequence = None
        self.id = "cached"
        self.model = "cached"
        self.type = "message"

    def __str__(self):
        return self.content[0].text if self.content else ""


class _CachedContentBlock:
    def __init__(self, text: str):
        self.text = text
        self.type = "text"


class _CachedUsage:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
