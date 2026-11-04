from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from bson import ObjectId


# -----------------------------
# Helper: convert ObjectId → str
# -----------------------------
class MongoBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


# -----------------------------
# Create DTO
# -----------------------------
class SchemeCreateDTO(BaseModel):
    name: str
    description: str
    amount: float
    req_docs: List[str]
    state: str


# -----------------------------
# Response DTO
# -----------------------------
class SchemeResponseDTO(MongoBaseModel):
    id: Optional[str] = Field(alias="_id")
    name: str
    description: str
    amount: float
    req_docs: List[str]
    state: str
