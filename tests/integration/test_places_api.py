import os
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from geoalchemy2.elements import WKTElement
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.db.session import get_engine, get_session, get_session_factory
from rus_map.main import create_app
from rus_map.models import (
    Material,
    MaterialRevision,
    MaterialType,
    ModerationStatus,
    Place,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_list_places_reads_postgis_data() -> None:
    """The HTTP endpoint returns a place inserted into PostgreSQL."""
    engine = get_engine()
    application = create_app()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
            )

            try:
                place = Place(
                    title="Завод Красный богатырь",
                    description="Integration-test record",
                    location=WKTElement(
                        "POINT(37.6917 55.8031)",
                        srid=4326,
                    ),
                )
                session.add(place)
                await session.flush()

                async def override_get_session() -> AsyncIterator[AsyncSession]:
                    yield session

                application.dependency_overrides[get_session] = override_get_session

                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/places")
                    detail_response = await client.get(
                        f"/api/v1/places/{place.id}",
                    )

                assert response.status_code == 200
                body = response.json()
                returned_place = next(
                    item for item in body["items"] if item["id"] == str(place.id)
                )
                assert returned_place == {
                    "id": str(place.id),
                    "title": "Завод Красный богатырь",
                    "latitude": 55.8031,
                    "longitude": 37.6917,
                }
                assert body["total"] >= 1
                assert detail_response.status_code == 200
                detail = detail_response.json()
                assert detail["id"] == str(place.id)
                assert detail["title"] == "Завод Красный богатырь"
                assert detail["description"] == "Integration-test record"
                assert detail["latitude"] == 55.8031
                assert detail["longitude"] == 37.6917
                assert detail["created_at"] is not None
                assert detail["updated_at"] is not None
            finally:
                application.dependency_overrides.clear()
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_place_commits_and_appears_in_list() -> None:
    """A place created through HTTP remains visible to the next request."""
    engine = get_engine()
    application = create_app()
    created_place_id: UUID | None = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as client:
            create_response = await client.post(
                "/api/v1/places",
                json={
                    "title": "Завод Красный богатырь",
                    "description": "Committed integration-test record",
                    "latitude": 55.8031,
                    "longitude": 37.6917,
                },
            )

            assert create_response.status_code == 201
            created = create_response.json()
            created_place_id = UUID(created["id"])
            assert created["latitude"] == 55.8031
            assert created["longitude"] == 37.6917
            assert created["created_at"] is not None
            assert created["updated_at"] is not None

            list_response = await client.get("/api/v1/places")

            assert list_response.status_code == 200
            returned_ids = {item["id"] for item in list_response.json()["items"]}
            assert str(created_place_id) in returned_ids
    finally:
        if created_place_id is not None:
            async with get_session_factory()() as cleanup_session:
                await cleanup_session.execute(
                    delete(Place).where(Place.id == created_place_id),
                )
                await cleanup_session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_materials_returns_only_published_latest_revision() -> None:
    """The nested endpoint filters moderation states and older revisions."""
    engine = get_engine()
    application = create_app()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                place = Place(
                    title="Кусковский химический завод",
                    description=None,
                    location=WKTElement("POINT(37.75 55.74)", srid=4326),
                )
                session.add(place)
                await session.flush()

                published = Material(
                    place_id=place.id,
                    type=MaterialType.EXTERNAL_LINK,
                    status=ModerationStatus.PUBLISHED,
                    title="Исторический материал",
                    source="Русь пролетарская",
                )
                pending = Material(
                    place_id=place.id,
                    type=MaterialType.TEXT,
                    status=ModerationStatus.PENDING_REVIEW,
                    title="Материал на проверке",
                    source=None,
                )
                session.add_all([published, pending])
                await session.flush()
                session.add_all(
                    [
                        MaterialRevision(
                            material_id=published.id,
                            revision_number=1,
                            status=ModerationStatus.PUBLISHED,
                            content=None,
                            url="https://example.com/old",
                        ),
                        MaterialRevision(
                            material_id=published.id,
                            revision_number=2,
                            status=ModerationStatus.PUBLISHED,
                            content=None,
                            url="https://example.com/current",
                        ),
                        MaterialRevision(
                            material_id=published.id,
                            revision_number=3,
                            status=ModerationStatus.PENDING_REVIEW,
                            content=None,
                            url="https://example.com/not-reviewed",
                        ),
                        MaterialRevision(
                            material_id=pending.id,
                            revision_number=1,
                            status=ModerationStatus.PENDING_REVIEW,
                            content="Этот текст ещё не опубликован",
                            url=None,
                        ),
                    ],
                )
                await session.flush()

                async def override_get_session() -> AsyncIterator[AsyncSession]:
                    yield session

                application.dependency_overrides[get_session] = override_get_session

                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        f"/api/v1/places/{place.id}/materials",
                    )

                assert response.status_code == 200
                body = response.json()
                assert body["total"] == 1
                assert len(body["items"]) == 1
                returned = body["items"][0]
                assert returned["id"] == str(published.id)
                assert returned["type"] == "external_link"
                assert returned["revision"]["revision_number"] == 2
                assert returned["revision"]["content"] is None
                assert returned["revision"]["url"] == ("https://example.com/current")
            finally:
                application.dependency_overrides.clear()
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
