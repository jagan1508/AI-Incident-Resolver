from typing import Optional
from typing_extensions import TypedDict

class State(TypedDict):
    incident_id: Optional[int]

    fingerprint: str
    event_type: str
    resource_name: str
    created_at: str
    raw_event: dict

    history: Optional[list]
    history_summary: Optional[str]
    
    classification: Optional[str]
    
    decision: Optional[str]
    reasoning: Optional[str]
    
    pod_status: Optional[str]         
    restart_count: Optional[int]      
    recent_k8s_events: Optional[list] 
    cluster_summary: Optional[str] 
    recommended_action: Optional[str]
    confidence: Optional[str]
    
    action_taken: Optional[str]
    outcome: Optional[str]

    
    