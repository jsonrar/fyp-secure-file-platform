from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SHELF_NAME_MAX_LENGTH = 100


def _collapse_whitespace(value: Any) -> Any:
    """Trim the name and fold runs of whitespace into single spaces.

    The name is only ever shown back to its owner, but "Work" and "Work " reaching the
    unique index as different shelves would give one account two entries it cannot tell
    apart, so the value is settled here rather than at the database.
    """
    if isinstance(value, str):
        return " ".join(value.split())
    return value


class _ShelfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _ShelfResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ShelfCreate(_ShelfRequest):
    name: Annotated[str, Field(min_length=1, max_length=SHELF_NAME_MAX_LENGTH)]

    _normalize_name = field_validator("name", mode="before")(_collapse_whitespace)


class ShelfRename(_ShelfRequest):
    name: Annotated[str, Field(min_length=1, max_length=SHELF_NAME_MAX_LENGTH)]

    _normalize_name = field_validator("name", mode="before")(_collapse_whitespace)


class FileMoveRequest(_ShelfRequest):
    """Where to file an owned upload. A null `shelf_id` returns it to the root."""

    shelf_id: UUID | None = None


class ShelfOut(_ShelfResponse):
    shelf_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class ShelfListOut(_ShelfResponse):
    shelves: list[ShelfOut]


class ShelfDeleteOut(_ShelfResponse):
    shelf_id: UUID
    deleted: bool = True
    # Nothing was removed but the shelf itself; saying how many files came back to the
    # root is what makes that visible to the caller.
    files_returned_to_root: int = Field(ge=0)


class AvatarMetaOut(_ShelfResponse):
    """What `/auth/avatar` mutations return; the image bytes are a separate GET."""

    has_avatar: bool
    content_type: str | None = None
    updated_at: datetime | None = None
    size_bytes: int | None = None
