from src.compressor import estimate_tokens, optimize_prompt, compress_conversation


class TestEstimateTokens:
    def test_rough_estimate(self):
        tokens = estimate_tokens("hello world")
        assert isinstance(tokens, int)
        assert tokens > 0


class TestOptimizePrompt:
    def test_removes_excess_whitespace(self):
        result = optimize_prompt("hello    world")
        assert "    " not in result

    def test_removes_html_comments(self):
        result = optimize_prompt("before <!-- comment --> after")
        assert "<!-- comment -->" not in result

    def test_preserves_content(self):
        result = optimize_prompt("hello world")
        assert "hello world" in result


class TestCompressConversation:
    def test_empty_messages(self):
        result = compress_conversation([], 1000)
        assert result == []

    def test_short_conversation_not_compressed(self):
        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = compress_conversation(msgs, 10000)
        assert len(result) == 2

    def test_long_conversation_compressed(self):
        msgs = [{"role": "user", "content": "A" * 1000}] * 50
        result = compress_conversation(msgs, 1000)
        assert len(result) < 50
