from __future__ import annotations

import asyncio
from unittest import mock

import pytest

from catchme.services.llm import LLM


def test_astream_rejects_responses_api_without_calling_chat_endpoint(monkeypatch):
    with mock.patch(
        "catchme.services.llm._load_llm_config", return_value={"wire_api": "responses"}
    ):
        llm = LLM()
    fake_aclient = mock.MagicMock()
    fake_aclient.chat.completions.create = mock.AsyncMock(return_value=[])
    llm._aclient = fake_aclient
    monkeypatch.setattr(llm, "_check_budget", lambda: None)

    async def consume_stream():
        return [chunk async for chunk in llm.astream([{"role": "user", "content": "synthetic"}])]

    with pytest.raises(NotImplementedError, match="streaming is not supported"):
        asyncio.run(consume_stream())

    fake_aclient.chat.completions.create.assert_not_awaited()
