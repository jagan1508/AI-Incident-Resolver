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
    
class Decision(BaseModel):
    decision: Literal["auto_remediate","escalate","ignore"] = Field(description="The recommended action to resolve the incident.")
    reasoning: str = Field(description="The reasoning behind the recommended action.")
    recommended_action: Literal["restart_pod", "scale_up", "rollback_deployment", "check_network", "investigate"] = Field(description="The specific action to be taken to resolve the incident.")
    confidence: Literal["high", "medium", "low"] = Field(description="The confidence level of the recommended action.")