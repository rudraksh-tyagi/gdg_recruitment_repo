import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RegistrationCreate(BaseModel):
    user_id: uuid.UUID


class RegistrationResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    registered_at: datetime

    model_config = ConfigDict(from_attributes=True)