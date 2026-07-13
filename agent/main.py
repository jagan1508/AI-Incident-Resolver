from agent.graph import graph
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
app=FastAPI()
class AgentRequest(BaseModel):
    incident_id: int
    fingerprint: str
    event_type: str
    resource_name: str
    raw_event: dict
    created_at: str

@app.post("/agent")
def agent_call(request: AgentRequest):
    state={
        "incident_id": request.incident_id,
        "fingerprint": request.fingerprint,
        "event_type": request.event_type,
        "resource_name": request.resource_name,
        "raw_event": request.raw_event,
        "created_at": request.created_at,
        "is_duplicate": False,
        "history": None,
        "history_summary": None,
        "classification": None,
        "decision": None,
        "reasoning": None,
        "pod_status": None,
        "restart_count": None,
        "recent_k8s_events": None,
        "cluster_summary": None,
        "action_taken": None,
        "outcome": None,
        "confidence": None,
        "recommended_action": None
        }
    result=graph.invoke(state)
    return {
        "decision":result["decision"],
        "actions_taken":result["action_taken"],
        "outcome":result["outcome"]
    }