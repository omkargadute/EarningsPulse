"""Regression tests for independent readers and complete tool traces."""

import asyncio

import pytest
from app.agents.trace_utils import traced_tool
from app.api.routes.playbook import stream_playbook_events
from app.models.playbook import PlaybookStatus
from app.services.job_store import JobStore
from app.services.sse_events import trace_event_to_sse


@pytest.mark.asyncio
async def test_readers_replay_then_receive_every_live_event_once():
    store = JobStore()
    await store.create("job", "AAPL")
    first = {"event_id": "one"}
    second = {"event_id": "two"}
    await store.append_trace("job", first)
    readers = [store.iter_traces("job") for _ in range(2)]
    assert await asyncio.gather(*(anext(reader) for reader in readers)) == [first, first]
    pending = [asyncio.ensure_future(anext(reader)) for reader in readers]
    await asyncio.sleep(0)
    await store.append_trace("job", second)
    assert await asyncio.wait_for(asyncio.gather(*pending), 1) == [second, second]
    await store.update_status("job", PlaybookStatus.COMPLETED)
    for reader in readers:
        with pytest.raises(StopAsyncIteration):
            await anext(reader)
    assert [event async for event in store.iter_traces("job")] == [first, second]


@pytest.mark.asyncio
async def test_cancelled_reader_does_not_consume_other_readers_events():
    store = JobStore()
    await store.create("job", "AAPL")
    reader = store.iter_traces("job")
    pending = asyncio.ensure_future(anext(reader))
    await asyncio.sleep(0)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    await store.append_trace("job", {"event_id": "one"})
    await store.update_status("job", PlaybookStatus.COMPLETED)
    assert [event async for event in store.iter_traces("job")] == [{"event_id": "one"}]


@pytest.mark.asyncio
async def test_heartbeat_and_failure_wake_reader_without_waiting_for_timeout():
    store = JobStore()
    await store.create("job", "AAPL")
    reader = store.iter_traces("job", heartbeat_seconds=0.01)
    assert await anext(reader) is None
    pending = asyncio.ensure_future(anext(reader))
    await asyncio.sleep(0)
    failure = {"event_id": "failed", "event_type": "run_failed"}
    await store.update_status("job", PlaybookStatus.FAILED, error="failed", trace_event=failure)
    assert await asyncio.wait_for(pending, 1) == failure
    with pytest.raises(StopAsyncIteration):
        await anext(reader)


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True])
async def test_tool_trace_records_outcome_and_preserves_exception(failed):
    events = []
    try:
        async with traced_tool("job", "research", "news", events=events):
            if failed:
                raise ValueError("provider unavailable")
    except ValueError as exc:
        assert str(exc) == "provider unavailable"
    assert [event["event_type"] for event in events] == [
        "tool_call_started",
        "tool_call_failed" if failed else "tool_call_completed",
    ]
    assert all(trace_event_to_sse(event)["type"] == "tool_call" for event in events)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [PlaybookStatus.COMPLETED, PlaybookStatus.FAILED])
async def test_stream_terminal_payload_matches_committed_job(status):
    store = JobStore()
    await store.create("job", "AAPL")
    response = await stream_playbook_events("job", store)
    await store.update_status(
        "job", status, error="provider unavailable" if status == PlaybookStatus.FAILED else None
    )
    chunks = [chunk async for chunk in response.body_iterator]
    assert len(chunks) == 1
    expected = '"type": "error"' if status == PlaybookStatus.FAILED else '"type": "playbook_ready"'
    assert isinstance(chunks[0], str)
    assert expected in chunks[0]
    assert (await store.get("job")).status == status
