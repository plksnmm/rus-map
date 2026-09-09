from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from rus_map.api.dependencies import (
    AdminSessionDependency,
    CsrfAdminSessionDependency,
    PlaceSubmissionServiceDependency,
)
from rus_map.models import SubmissionStatus
from rus_map.repositories.submission import PlaceSubmissionRecord
from rus_map.schemas.submission import (
    PlaceSubmissionDecision,
    PlaceSubmissionListResponse,
    PlaceSubmissionResponse,
)
from rus_map.services.submission import (
    InvalidSubmissionTransition,
    SubmissionNotFound,
)

router = APIRouter(prefix="/admin/submissions", tags=["admin-submissions"])


def response_from_record(record: PlaceSubmissionRecord) -> PlaceSubmissionResponse:
    return PlaceSubmissionResponse.model_validate(record)


def raise_http_error(error: Exception) -> NoReturn:
    if isinstance(error, SubmissionNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(error),
    ) from error


@router.get("", response_model=PlaceSubmissionListResponse)
async def list_submissions(
    response: Response,
    service: PlaceSubmissionServiceDependency,
    _admin: AdminSessionDependency,
    submission_status: Annotated[SubmissionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PlaceSubmissionListResponse:
    items, total = await service.list(
        submission_status,
        limit=limit,
        offset=offset,
    )
    response.headers["Cache-Control"] = "no-store"
    return PlaceSubmissionListResponse(
        items=[response_from_record(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{submission_id}", response_model=PlaceSubmissionResponse)
async def get_submission(
    submission_id: UUID,
    response: Response,
    service: PlaceSubmissionServiceDependency,
    _admin: AdminSessionDependency,
) -> PlaceSubmissionResponse:
    try:
        submission = await service.get(submission_id)
    except SubmissionNotFound as error:
        raise_http_error(error)
    response.headers["Cache-Control"] = "no-store"
    return response_from_record(submission)


@router.post("/{submission_id}/approve", response_model=PlaceSubmissionResponse)
async def approve_submission(
    submission_id: UUID,
    decision: PlaceSubmissionDecision,
    response: Response,
    service: PlaceSubmissionServiceDependency,
    admin: CsrfAdminSessionDependency,
) -> PlaceSubmissionResponse:
    try:
        submission = await service.approve(
            submission_id,
            admin.admin_id,
            decision.review_notes,
        )
    except (SubmissionNotFound, InvalidSubmissionTransition) as error:
        raise_http_error(error)
    response.headers["Cache-Control"] = "no-store"
    return response_from_record(submission)


@router.post("/{submission_id}/reject", response_model=PlaceSubmissionResponse)
async def reject_submission(
    submission_id: UUID,
    decision: PlaceSubmissionDecision,
    response: Response,
    service: PlaceSubmissionServiceDependency,
    admin: CsrfAdminSessionDependency,
) -> PlaceSubmissionResponse:
    try:
        submission = await service.reject(
            submission_id,
            admin.admin_id,
            decision.review_notes,
        )
    except (SubmissionNotFound, InvalidSubmissionTransition) as error:
        raise_http_error(error)
    response.headers["Cache-Control"] = "no-store"
    return response_from_record(submission)
