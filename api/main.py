from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2


app = FastAPI()

class Incident(BaseModel):
    actions_taken: str
    outcome: str
    notes: str
    
def get_db_connection():
    conn=psycopg2.connect(host="localhost",database="incident_db", user="postgres" , password="password")
    return conn
        

@app.get("/")
def root():
    return {"message": "OpsAgent API is running."}

@app.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int,body: Incident):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("Select id,fingerprint,decision,outcome from incidents where id=%s",(incident_id,))
                incident = cursor.fetchone()
                if not incident:
                    return HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
                if incident[2] != "escalate":
                    return HTTPException(status_code=400, detail=f"Incident {incident_id} is not in an escalated state.")
                if incident[3] =="resolved":
                    return HTTPException(status_code=400, detail=f"Incident {incident_id} has already been resolved.")
                cursor.execute(
                    "UPDATE incidents SET actions_taken = %s, outcome = %s, notes = %s WHERE id = %s",
                    (body.actions_taken, body.outcome, body.notes, incident_id)
                )
                conn.commit()
                return {"status": "success", "id": incident_id, "actions_taken": body.actions_taken, "outcome": body.outcome, "notes": body.notes}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select id,fingerprint,event_type,classification,created_at,decision,outcome from incidents where id=%s",(incident_id,))
                incident=cursor.fetchone()
                if not incident:
                    return HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
                return {
                    "id": incident[0],
                    "fingerprint": incident[1],
                    "event_type": incident[2],
                    "classification": incident[3],
                    "created_at": incident[4],
                    "decision": incident[5],
                    "outcome": incident[6]
                }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
            