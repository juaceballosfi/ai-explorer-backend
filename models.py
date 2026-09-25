from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str


class DocumentUploadResponse(BaseModel):
    id: int
    name: str
    size: int
    message: str
