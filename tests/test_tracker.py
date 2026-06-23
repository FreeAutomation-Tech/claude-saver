from src.tracker import get_model_cost, get_usage_stats


class TestGetModelCost:
    def test_known_model(self):
        cost = get_model_cost("claude-3-opus-20240229")
        assert cost["input"] == 15.0
        assert cost["output"] == 75.0

    def test_unknown_model_defaults(self):
        cost = get_model_cost("unknown-model")
        assert cost["input"] == 3.0
        assert cost["output"] == 15.0


class TestGetUsageStats:
    def test_stats_structure(self):
        stats = get_usage_stats(30)
        assert "total_requests" in stats
        assert "total_cost" in stats
        assert "total_saved" in stats
        assert "daily" in stats
        assert "model_breakdown" in stats
        assert "savings_rate" in stats
