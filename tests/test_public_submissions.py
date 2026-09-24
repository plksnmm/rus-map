from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from rus_map.api.dependencies import get_place_submission_service
from rus_map.api.routes import submissions
from rus_map.main import create_app
from rus_map.models import SubmissionStatus
from rus_map.repositories.submission import PlaceSubmissionRecord


@pytest.fixture(autouse=True)
def reset_rate_limit() -> None:
    submissions._requests.clear()


def pending_record() -> PlaceSubmissionRecord:
    now = datetime.now(UTC)
    return PlaceSubmissionRecord(
        id=uuid4(),
        status=SubmissionStatus.PENDING,
        title="Завод Красный богатырь",
        description="Историческое предприятие",
        latitude=55.8031,
        longitude=37.6917,
        source_urls=("https://example.com/factory",),
        address="Москва, Краснобогатырская улица, 2",
        review_notes=None,
        approved_place_id=None,
        moderated_by_admin_id=None,
        moderated_at=None,
        created_at=now,
        updated_at=now,
    )


def test_public_submission_enters_moderation_queue() -> None:
    service = MagicMock()
    record = pending_record()
    service.create = AsyncMock(return_value=record)
    application = create_app()
    application.dependency_overrides[get_place_submission_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/submissions",
            headers={"X-Real-IP": "192.0.2.10"},
            json={
                "title": record.title,
                "description": record.description,
                "latitude": record.latitude,
                "longitude": record.longitude,
                "address": record.address,
                "source_urls": list(record.source_urls),
                "website": "",
            },
        )

    assert response.status_code == 202
    assert response.json() == {
        "id": str(record.id),
        "status": "pending",
        "created_at": record.created_at.isoformat().replace("+00:00", "Z"),
    }
    assert response.headers["cache-control"] == "no-store"
    proposal = service.create.await_args.args[0]
    assert proposal.title == record.title
    assert proposal.address == record.address
    assert proposal.source_urls == record.source_urls


def test_honeypot_is_acknowledged_without_storing_submission() -> None:
    service = MagicMock()
    service.create = AsyncMock()
    application = create_app()
    application.dependency_overrides[get_place_submission_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/submissions",
            json={
                "title": "Spam factory",
                "latitude": 55.8,
                "longitude": 37.6,
                "website": "buy.example",
            },
        )

    assert response.status_code == 202
    service.create.assert_not_awaited()


def test_public_submission_is_rate_limited_by_client_ip() -> None:
    service = MagicMock()
    service.create = AsyncMock(return_value=pending_record())
    application = create_app()
    application.dependency_overrides[get_place_submission_service] = lambda: service
    payload = {"title": "Factory", "latitude": 55.8, "longitude": 37.6}

    with TestClient(application) as client:
        responses = [
            client.post(
                "/api/v1/submissions",
                headers={"X-Real-IP": "192.0.2.20"},
                json=payload,
            )
            for _ in range(submissions.RATE_LIMIT + 1)
        ]

    assert all(response.status_code == 202 for response in responses[:-1])
    assert responses[-1].status_code == 429
    assert responses[-1].headers["retry-after"] == str(submissions.RATE_WINDOW_SECONDS)
