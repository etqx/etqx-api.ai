from pydantic import BaseModel


class ProtocolItem(BaseModel):
    id: str
    name: str


class ProtocolDoc(BaseModel):
    id: str
    name: str
    prompt_text: str

