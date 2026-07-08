from kafka import KafkaConsumer
import psycopg2
import json
import redis
from agent.graph import graph

consumer = KafkaConsumer('demo', bootstrap_servers='localhost:9092', value_deserializer=lambda m: json.loads(m.decode('utf-8')))



r = redis.Redis(host='localhost', port=6379, decode_responses=True)


try:
    with psycopg2.connect(
        host="localhost",
        database="incident_db", user="postgres" , password="password") as conn:
        with conn.cursor() as cursor:
            for message in consumer:
                event = message.value
                print(f"Received event: {event}")
                status=r.set(event["fingerprint"],json.dumps(event),ex=30,nx=True)
                if status:          
                    cursor.execute(
                        "INSERT INTO incidents (event_type, resource_name, fingerprint, raw_event, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (event["type"], event["resource"], event["fingerprint"], json.dumps(event), event["timestamp"]) 
                    )
                    conn.commit()
                    row=cursor.fetchone()
                    if row:
                        event_id=row[0]
                    print(f"Inserted event into database with ID: {event_id}")
                    initial_state = {
                        "incident_id": event_id,
                        "fingerprint": event["fingerprint"],
                        "event_type": event["type"],
                        "resource_name": event["resource"],
                        "raw_event": event,
                        "created_at": event["timestamp"],
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
                    graph_result = graph.invoke(initial_state)
                    print(f"Agent completed: decision={graph_result['decision']}, outcome={graph_result['outcome']}")
                else:
                    print(f"Duplicate suppressed: {event['fingerprint']}")
except (Exception, psycopg2.DatabaseError) as error:
    print(error)