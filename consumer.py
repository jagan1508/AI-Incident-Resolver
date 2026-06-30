from kafka import KafkaConsumer
import psycopg2
import json
import redis

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
                else:
                    print(f"Duplicate suppressed: {event['fingerprint']}")
except (Exception, psycopg2.DatabaseError) as error:
    print(error)