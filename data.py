from typing import Optional

from pydantic import BaseModel


class Message(BaseModel):
    user_id: int
    message: str
    attending_provider_id: Optional[int]
