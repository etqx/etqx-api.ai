from pydantic import BaseModel


class CapabilityItem(BaseModel):
    id: str
    name: str


class CapabilityDoc(BaseModel):
    id: str
    name: str
    prompt_text: str

