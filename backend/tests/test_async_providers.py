"""Slow synchronous providers must leave the API event loop available."""

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.config import Settings
from app.models.data import HistoricalEarningsResponse
from app.services.earnings_calendar import EarningsCalendarService
from app.services.peer_map import PeerMapService
from app.services.reaction_analyzer import ReactionAnalyzer


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["history", "next_date", "reaction", "peers"])
async def test_provider_wait_does_not_block_other_coroutines(operation, monkeypatch, cache):
    started = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    history = HistoricalEarningsResponse(ticker="AAPL", events=[], source="yfinance")
    earnings = MagicMock()
    earnings.get_historical_earnings = AsyncMock(return_value=history)
    earnings.get_peers = AsyncMock(return_value=[])
    if operation in {"history", "next_date"}:
        service = EarningsCalendarService(settings=Settings(finnhub_api_key=None), cache=cache)
        method = (
            "_fetch_historical_from_yfinance"
            if operation == "history"
            else "_get_next_earnings_from_yfinance"
        )
        result = history if operation == "history" else None
        call = (
            service.get_historical_earnings
            if operation == "history"
            else service.get_next_earnings_date
        )
    elif operation == "reaction":
        price = MagicMock()
        price.get_options_implied_move.return_value = None
        service = ReactionAnalyzer(earnings_service=earnings, price_service=price, cache=cache)
        method, result, call = "_analyze_events_batch", ([], []), service.analyze_ticker
    else:
        service = PeerMapService(earnings_service=earnings, cache=cache)
        method, result, call = "_load_correlation_bars", {}, service.build_peer_map

    def slow_provider(*args, **kwargs):
        loop.call_soon_threadsafe(started.set)
        release.wait(timeout=2)
        return result

    monkeypatch.setattr(service, method, slow_provider)
    task = asyncio.create_task(call("AAPL"))
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        # This coroutine must resume while the provider is still waiting.
        assert not task.done()
    finally:
        release.set()
        await task
