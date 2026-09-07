from uuid import UUID

from rus_map.models import SubmissionStatus
from rus_map.repositories.place import NewPlace, PlaceRepository
from rus_map.repositories.submission import (
    NewPlaceSubmission,
    PlaceSubmissionRecord,
    PlaceSubmissionRepository,
)


class SubmissionNotFound(LookupError):
    """Raised when a moderation target does not exist."""


class InvalidSubmissionTransition(ValueError):
    """Raised when a final moderation decision would be reversed."""


class PlaceSubmissionService:
    """Coordinate proposal decisions inside the caller's transaction."""

    def __init__(
        self,
        submissions: PlaceSubmissionRepository,
        places: PlaceRepository,
    ) -> None:
        self._submissions = submissions
        self._places = places

    async def create(self, proposal: NewPlaceSubmission) -> PlaceSubmissionRecord:
        """Store a proposal without publishing a place."""
        return await self._submissions.create(proposal)

    async def approve(
        self,
        submission_id: UUID,
        review_notes: str | None = None,
    ) -> PlaceSubmissionRecord:
        """Publish one pending proposal, or return its existing approval."""
        submission = await self._require_locked(submission_id)

        if submission.status is SubmissionStatus.APPROVED:
            return submission
        if submission.status is SubmissionStatus.REJECTED:
            raise InvalidSubmissionTransition(
                "a rejected submission cannot be approved"
            )

        place = await self._places.create(
            NewPlace(
                title=submission.title,
                description=submission.description,
                latitude=submission.latitude,
                longitude=submission.longitude,
            ),
        )
        approved = await self._submissions.mark_approved(
            submission.id,
            place.id,
            review_notes,
        )
        if approved is None:
            raise RuntimeError("submission changed while its row was locked")
        return approved

    async def reject(
        self,
        submission_id: UUID,
        review_notes: str | None = None,
    ) -> PlaceSubmissionRecord:
        """Reject one pending proposal, preserving final decisions."""
        submission = await self._require_locked(submission_id)

        if submission.status is SubmissionStatus.REJECTED:
            return submission
        if submission.status is SubmissionStatus.APPROVED:
            raise InvalidSubmissionTransition(
                "an approved submission cannot be rejected"
            )

        rejected = await self._submissions.mark_rejected(
            submission.id,
            review_notes,
        )
        if rejected is None:
            raise RuntimeError("submission changed while its row was locked")
        return rejected

    async def _require_locked(self, submission_id: UUID) -> PlaceSubmissionRecord:
        submission = await self._submissions.get_for_update(submission_id)
        if submission is None:
            raise SubmissionNotFound(str(submission_id))
        return submission
