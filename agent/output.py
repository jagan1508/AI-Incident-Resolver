from pydantic import BaseModel,Field
from typing import Literal
class Category(BaseModel):
    category: Literal[
        "container_failure", 
        "resource_exhaustion", 
        "deployment_failure", 
        "network_issue", 
        "unknown"
    ] = Field(description="The exact kubernetes event classification category.")