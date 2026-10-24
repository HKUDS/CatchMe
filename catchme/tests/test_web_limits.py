from __future__ import annotations

import pytest

from catchme import web
from catchme.store import Event


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("/api/events?limit=-1", []),
        ("/api/timeline?limit=-1", {"since": None, "until": None, "tracks": {}}),
        ("/api/search?q=synthetic&limit=-1", []),
    ],
)
def test_negative_limit_does_not_remove_api_result_bound(url, expected, store, monkeypatch):
    store.insert_raw(
        [
            Event(timestamp=1_700_000_000 + index, kind="test", data={"text": "synthetic"})
            for index in range(3)
        ]
    )
    monkeypatch.setattr(web, "get_store", lambda: store)

    response = web.app.test_client().get(url)

    assert response.status_code == 200
    assert response.get_json() == expected
