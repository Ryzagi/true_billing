from typing import Optional

from pydantic import BaseModel


class Message(BaseModel):
    user_id: int
    message: str
    provider_id: Optional[int]
