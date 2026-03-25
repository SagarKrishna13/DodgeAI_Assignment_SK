from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str
    history: Optional[List[dict]] = []

class SubgraphRequest(BaseModel):
    entity_ids: List[str]
