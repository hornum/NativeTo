from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    receiver_id: int
    text: str = Field(min_length=1, max_length=2000)
