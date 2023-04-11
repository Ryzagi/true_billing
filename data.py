from typing import Optional

from pydantic import BaseModel

# # The Message class defines a data model for a message that includes a user ID and a message text. It also includes an
# optional provider ID field, which is used to identify the healthcare provider associated with the message (if any).
# The provider ID field is optional because not all messages may be associated with a provider. By inheriting from the
# BaseModel class, the Message class gains additional functionality provided by pydantic, such as automatic validation
# of input data.


class Message(BaseModel):
    user_id: int
    message: str
    provider_id: Optional[int]
