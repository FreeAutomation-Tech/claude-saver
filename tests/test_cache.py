from src.cache import _text_hash, get_cache_stats, clear_cache


class TestTextHash:
    def test_hash_consistency(self):
        h1 = _text_hash("hello world")
        h2 = _text_hash("hello world")
        assert h1 == h2

    def test_hash_different_inputs(self):
        h1 = _text_hash("hello world")
        h2 = _text_hash("hello world!")
        assert h1 != h2


class TestClearCache:
    def test_clear_cache_does_not_raise(self):
        clear_cache()
        stats = get_cache_stats()
        assert stats["total_cached"] == 0


class TestGetCacheStats:
    def test_stats_return_structure(self):
        clear_cache()
        stats = get_cache_stats()
        assert "total_cached" in stats
        assert "total_hits" in stats
        assert "total_tokens_saved" in stats
        assert "newest_entry" in stats
        assert "oldest_entry" in stats
