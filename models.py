from pydantic import BaseModel
from typing import List

class QuestionRequest(BaseModel):
    pregunta: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage] = []
    nueva_pregunta: str

class DocumentUploadResponse(BaseModel):
    id: int
    name: str
    size: int
    message: str