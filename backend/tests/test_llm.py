"""Tests for LLM client provider fallback chain."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.llm import GOOGLE_MODEL_FALLBACKS, LLMClient
from app.config import Settings


@pytest.fixture
def fallback() -> dict:
    return {"result": "fallback"}


@pytest.mark.asyncio
async def test_invoke_json_no_keys_uses_fallback(fallback):
    settings = Settings(openai_api_key=None, google_api_key=None)
    client = LLMClient(settings=settings)

    assert not client.enabled
    result = await client.invoke_json(
        system_prompt="sys",
        user_prompt="user",
        fallback=fallback,
    )
    assert result == fallback


@pytest.mark.asyncio
async def test_invoke_json_openai_success(fallback):
    settings = Settings(openai_api_key="sk-test", google_api_key="google-test")
    client = LLMClient(settings=settings)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content='{"beat_probability": 0.5}'))

    with patch("langchain_openai.ChatOpenAI", return_value=mock_llm):
        result = await client.invoke_json(
            system_prompt="sys",
            user_prompt="user",
            fallback=fallback,
        )

    assert result == {"beat_probability": 0.5}
    mock_llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_invoke_json_openai_fails_google_succeeds(fallback):
    settings = Settings(
        openai_api_key="sk-test",
        google_api_key="google-test",
        google_llm_model="gemma-4-31b-it",
    )
    client = LLMClient(settings=settings)

    mock_openai = MagicMock()
    mock_openai.ainvoke = AsyncMock(side_effect=Exception("credit_balance_exhausted"))

    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(
        return_value=MagicMock(text='{"beat_probability": 0.7}')
    )

    with (
        patch("langchain_openai.ChatOpenAI", return_value=mock_openai),
        patch("google.generativeai.GenerativeModel", return_value=mock_model),
        patch("google.generativeai.configure"),
    ):
        result = await client.invoke_json(
            system_prompt="sys",
            user_prompt="user",
            fallback=fallback,
        )

    assert result == {"beat_probability": 0.7}
    mock_model.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_invoke_json_both_fail_uses_fallback(fallback):
    settings = Settings(openai_api_key="sk-test", google_api_key="google-test")
    client = LLMClient(settings=settings)

    mock_openai = MagicMock()
    mock_openai.ainvoke = AsyncMock(side_effect=Exception("openai down"))

    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(side_effect=Exception("google down"))

    with (
        patch("langchain_openai.ChatOpenAI", return_value=mock_openai),
        patch("google.generativeai.GenerativeModel", return_value=mock_model),
        patch("google.generativeai.configure"),
    ):
        result = await client.invoke_json(
            system_prompt="sys",
            user_prompt="user",
            fallback=fallback,
        )

    assert result == fallback


@pytest.mark.asyncio
async def test_invoke_json_google_only(fallback):
    settings = Settings(openai_api_key=None, google_api_key="google-test")
    client = LLMClient(settings=settings)

    assert client.enabled

    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(
        return_value=MagicMock(text='{"inline_probability": 0.4}')
    )

    with (
        patch("google.generativeai.GenerativeModel", return_value=mock_model),
        patch("google.generativeai.configure"),
    ):
        result = await client.invoke_json(
            system_prompt="sys",
            user_prompt="user",
            fallback=fallback,
        )

    assert result == {"inline_probability": 0.4}


@pytest.mark.asyncio
async def test_invoke_json_google_tries_next_model_on_404(fallback):
    settings = Settings(
        openai_api_key=None, google_api_key="google-test", google_llm_model="gemma-3-27b-it"
    )
    client = LLMClient(settings=settings)

    unavailable = Exception("404 models/gemma-3-27b-it is not found")
    success_model = MagicMock()
    success_model.generate_content = MagicMock(
        return_value=MagicMock(text='{"beat_probability": 0.6}')
    )

    def make_model(*, model_name: str, **kwargs):
        if model_name == "gemma-3-27b-it":
            model = MagicMock()
            model.generate_content = MagicMock(side_effect=unavailable)
            return model
        if model_name == GOOGLE_MODEL_FALLBACKS[0]:
            return success_model
        raise AssertionError(f"unexpected model {model_name}")

    with (
        patch("google.generativeai.GenerativeModel", side_effect=make_model),
        patch("google.generativeai.configure"),
    ):
        result = await client.invoke_json(
            system_prompt="sys",
            user_prompt="user",
            fallback=fallback,
        )

    assert result == {"beat_probability": 0.6}
    success_model.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_openai_json_keeps_existing_fallback_policy(fallback):
    client = LLMClient(settings=Settings(openai_api_key="test", google_api_key="test"))
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="not JSON"))
    with (
        patch("langchain_openai.ChatOpenAI", return_value=mock_llm),
        patch.object(client, "_invoke_google", new_callable=AsyncMock) as google,
    ):
        assert (
            await client.invoke_json(system_prompt="sys", user_prompt="user", fallback=fallback)
            == fallback
        )
    google.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,expected", [("openai", ["openai", "google"]), (" Google ", ["google", "openai"])]
)
async def test_configured_provider_order_is_preserved(provider, expected, fallback):
    client = LLMClient(
        settings=Settings(openai_api_key="test", google_api_key="test", llm_provider=provider)
    )
    calls = []

    async def openai(*args):
        calls.append("openai")
        raise RuntimeError("unavailable")

    async def google(*args):
        calls.append("google")
        raise RuntimeError("unavailable")

    with (
        patch.object(client, "_invoke_openai", openai),
        patch.object(client, "_invoke_google", google),
    ):
        assert (
            await client.invoke_json(system_prompt="sys", user_prompt="user", fallback=fallback)
            == fallback
        )
    assert calls == expected
