import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.event import Event
from app.models.registration import Registration
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse
from app.schemas.registration import (
    RegistrationCreate,
    RegistrationResponse,
)


router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:

    if event_data.start_time >= event_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time",
        )

    organizer_result = await db.execute(
        select(User).where(User.id == event_data.organizer_id)
    )

    organizer = organizer_result.scalar_one_or_none()

    if organizer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizer not found",
        )

    event = Event(
        title=event_data.title,
        description=event_data.description,
        location=event_data.location,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        capacity=event_data.capacity,
        organizer_id=event_data.organizer_id,
    )

    db.add(event)

    await db.commit()
    await db.refresh(event)

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        location=event.location,
        start_time=event.start_time,
        end_time=event.end_time,
        capacity=event.capacity,
        organizer_id=event.organizer_id,
        created_at=event.created_at,
        registration_count=0,
        remaining_seats=event.capacity,
    )


@router.get(
    "",
    response_model=list[EventResponse],
)
async def list_events(
    db: AsyncSession = Depends(get_db),
) -> list[EventResponse]:

    registration_count = (
        select(
            Registration.event_id,
            func.count(Registration.id).label("registration_count"),
        )
        .group_by(Registration.event_id)
        .subquery()
    )

    query = (
        select(
            Event,
            func.coalesce(
                registration_count.c.registration_count,
                0,
            ).label("registration_count"),
        )
        .outerjoin(
            registration_count,
            Event.id == registration_count.c.event_id,
        )
        .order_by(Event.start_time)
    )

    result = await db.execute(query)

    rows = result.all()

    events: list[EventResponse] = []

    for event, count in rows:
        count = int(count)

        events.append(
            EventResponse(
                id=event.id,
                title=event.title,
                description=event.description,
                location=event.location,
                start_time=event.start_time,
                end_time=event.end_time,
                capacity=event.capacity,
                organizer_id=event.organizer_id,
                created_at=event.created_at,
                registration_count=count,
                remaining_seats=max(event.capacity - count, 0),
            )
        )

    return events


@router.get(
    "/{event_id}",
    response_model=EventResponse,
)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:

    event_result = await db.execute(
        select(Event).where(Event.id == event_id)
    )

    event = event_result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    count_result = await db.execute(
        select(func.count(Registration.id)).where(
            Registration.event_id == event_id
        )
    )

    registration_count = count_result.scalar_one() or 0

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        location=event.location,
        start_time=event.start_time,
        end_time=event.end_time,
        capacity=event.capacity,
        organizer_id=event.organizer_id,
        created_at=event.created_at,
        registration_count=int(registration_count),
        remaining_seats=max(
            event.capacity - int(registration_count),
            0,
        ),
    )


@router.post(
    "/{event_id}/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    event_id: uuid.UUID,
    registration_data: RegistrationCreate,
    db: AsyncSession = Depends(get_db),
) -> RegistrationResponse:

    async with db.begin():

        # ---------------------------------------------------------
        # 1. Lock the event row.
        #
        # PostgreSQL will make concurrent registration requests
        # wait for this transaction to release the lock.
        # ---------------------------------------------------------
        event_result = await db.execute(
            select(Event)
            .where(Event.id == event_id)
            .with_for_update()
        )

        event = event_result.scalar_one_or_none()

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )

        # ---------------------------------------------------------
        # 2. Verify that the user exists.
        # ---------------------------------------------------------
        user_result = await db.execute(
            select(User).where(
                User.id == registration_data.user_id
            )
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # ---------------------------------------------------------
        # 3. Check for duplicate registration.
        # ---------------------------------------------------------
        existing_registration_result = await db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.user_id == registration_data.user_id,
            )
        )

        existing_registration = (
            existing_registration_result.scalar_one_or_none()
        )

        if existing_registration is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already registered",
            )

        # ---------------------------------------------------------
        # 4. Dynamically count registrations.
        # ---------------------------------------------------------
        count_result = await db.execute(
            select(func.count(Registration.id)).where(
                Registration.event_id == event_id
            )
        )

        current_registrations = count_result.scalar_one() or 0

        # ---------------------------------------------------------
        # 5. Capacity check.
        #
        # Because the event row is locked, another registration
        # cannot pass this check simultaneously for this event.
        # ---------------------------------------------------------
        if current_registrations >= event.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event capacity reached",
            )

        # ---------------------------------------------------------
        # 6. Create registration.
        # ---------------------------------------------------------
        registration = Registration(
            event_id=event_id,
            user_id=registration_data.user_id,
        )

        db.add(registration)

        try:
            await db.flush()
        except IntegrityError:
            # Database-level UNIQUE constraint provides a final
            # safeguard against duplicate registrations.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already registered",
            )

    # Transaction commits automatically when leaving db.begin()
    await db.refresh(registration)

    return RegistrationResponse(
        id=registration.id,
        event_id=registration.event_id,
        user_id=registration.user_id,
        registered_at=registration.registered_at,
    )