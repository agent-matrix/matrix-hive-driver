from matrix_hive_driver.runtime.llm_provider import (
    LLMResponse,
    NoOpProvider,
    OllamaProvider,
    get_llm_provider,
)


def test_noop_provider_always_ok():
    p = NoOpProvider()
    resp = p.complete("Hello")
    assert resp.ok is True
    assert resp.provider == "noop"
    assert resp.text == ""


def test_noop_provider_is_available():
    p = NoOpProvider()
    assert p.is_available() is True


def test_ollama_graceful_degradation():
    """OllamaProvider returns ok=False when Ollama is unreachable."""
    p = OllamaProvider(base_url="http://127.0.0.1:1", model="llama3.1:8b")
    resp = p.complete("test")
    assert resp.ok is False
    assert resp.provider == "ollama"
    assert resp.error is not None
    assert "unreachable" in resp.error.lower() or "Ollama" in resp.error


def test_ollama_is_available_false_when_down():
    p = OllamaProvider(base_url="http://127.0.0.1:1", model="llama3.1:8b")
    assert p.is_available() is False


def test_get_llm_provider_default_noop(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    # Re-import to pick up env
    from matrix_hive_driver.driver.config import Settings

    s = Settings()
    assert s.llm_provider == "none"
    p = get_llm_provider()
    assert isinstance(p, NoOpProvider)


def test_llm_response_dataclass():
    r = LLMResponse(text="hi", model="test", provider="test", ok=True)
    assert r.text == "hi"
    assert r.error is None
