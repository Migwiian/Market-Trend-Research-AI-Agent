from synthesis.client import LLMConfig, model_name_for_tier


def test_model_name_for_tier_fast():
    cfg = LLMConfig(fast_model="fast-3b", standard_model="std-8b")
    assert model_name_for_tier("fast", cfg) == "fast-3b"


def test_model_name_for_tier_standard():
    cfg = LLMConfig(fast_model="fast-3b", standard_model="std-8b")
    assert model_name_for_tier("standard", cfg) == "std-8b"
