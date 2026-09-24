from collections import OrderedDict, deque
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, status

from rus_map.api.dependencies import PlaceSubmissionServiceDependency
from rus_map.models import SubmissionStatus
from rus_map.repositories.submission import NewPlaceSubmission
from rus_map.schemas.submission import PlaceSubmissionCreate, PlaceSubmissionReceipt

router = APIRouter(prefix="/submissions", tags=["submissions"])

RATE_LIMIT = 5
RATE_WINDOW_SECONDS = 60 * 60
MAX_RATE_LIMIT_CLIENTS = 10_000
_requests: OrderedDict[str, deque[float]] = OrderedDict()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("X-Real-IP")
    if forwarded:
        return forwarded.strip()
    if request.client:
        return request.client.host
    return "unknown"


def _check_rate_limit(request: Request) -> None:
    now = monotonic()
    key = _client_key(request)
    attempts = _requests.setdefault(key, deque())
    _requests.move_to_end(key)
    while len(_requests) > MAX_RATE_LIMIT_CLIENTS:
        _requests.popitem(last=False)
    while attempts and attempts[0] <= now - RATE_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions; try again later",
            headers={"Retry-After": str(RATE_WINDOW_SECONDS)},
        )
    attempts.append(now)


@router.post(
    "",
    response_model=PlaceSubmissionReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_submission(
    proposal: PlaceSubmissionCreate,
    request: Request,
    response: Response,
    service: PlaceSubmissionServiceDependency,
) -> PlaceSubmissionReceipt:
    """Accept an anonymous proposal for moderation without publishing it."""
    _check_rate_limit(request)
    response.headers["Cache-Control"] = "no-store"

    # The hidden field is intentionally accepted. Bots receive a normal-looking
    # acknowledgement while their payload never reaches the moderation queue.
    if proposal.website:
        return PlaceSubmissionReceipt(
            id=uuid4(),
            status=SubmissionStatus.PENDING,
            created_at=datetime.now(UTC),
        )

    created = await service.create(
        NewPlaceSubmission(
            title=proposal.title,
            description=proposal.description,
            latitude=proposal.latitude,
            longitude=proposal.longitude,
            source_urls=tuple(str(url) for url in proposal.source_urls),
            address=proposal.address,
        )
    )
    return PlaceSubmissionReceipt(
        id=created.id,
        status=created.status,
        created_at=created.created_at,
    )
