from unittest.mock import patch

from src.saver_client import SaverAnthropic, _CachedResponse


class TestSaverAnthropicInit:
    def test_init_without_api_key_uses_env(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            client = SaverAnthropic()
            assert client._api_key == "sk-test"

    def test_init_stats(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            client = SaverAnthropic()
            assert client._stats["cache_hits"] == 0
            assert client._stats["cache_misses"] == 0


class TestSaverAnthropicConfigure:
    def setup_method(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            self.client = SaverAnthropic()

    def test_disable_cache(self):
        self.client.configure(cache=False)
        assert self.client._cache_enabled is False

    def test_disable_compress(self):
        self.client.configure(compress=False)
        assert self.client._compress_enabled is False

    def test_set_max_context(self):
        self.client.configure(max_context_tokens=2000)
        assert self.client._max_context_tokens == 2000


class TestSaverAnthropicStats:
    def setup_method(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            self.client = SaverAnthropic()

    def test_get_stats(self):
        stats = self.client.get_stats()
        assert "cache_hits" in stats
        assert "cache_misses" in stats

    def test_reset_stats(self):
        self.client._stats["cache_hits"] = 5
        self.client.reset_stats()
        assert self.client._stats["cache_hits"] == 0


class TestCachedResponse:
    def test_cached_response_str(self):
        resp = _CachedResponse("hello world")
        assert str(resp) == "hello world"

    def test_cached_response_content(self):
        resp = _CachedResponse("hello world")
        assert resp.content[0].text == "hello world"
        assert resp.stop_reason == "end_turn"
