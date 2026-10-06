import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    location: str = Field(..., min_length=1, max_length=255)
    start_time: datetime
    end_time: datetime
    capacity: int = Field(..., gt=0)
    organizer_id: uuid.UUID

    @field_validator("end_time")
    @classmethod
    def validate_end_time(
        cls,
        end_time: datetime,
        info,
    ) -> datetime:
        start_time = info.data.get("start_time")

        if start_time is not None and start_time >= end_time:
            raise ValueError("start_time must be before end_time")

        return end_time


class EventUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    location: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    start_time: datetime | None = None

    end_time: datetime | None = None

    capacity: int | None = Field(
        default=None,
        gt=0,
    )


class EventResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    organizer_id: uuid.UUID
    created_at: datetime
    registration_count: int
    remaining_seats: int

    model_config = ConfigDict(from_attributes=True)