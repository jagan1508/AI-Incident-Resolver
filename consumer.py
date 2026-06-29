from kafka import KafkaConsumer
import psycopg2
import json

consumer = KafkaConsumer('demo', bootstrap_servers='localhost:9092', value_deserializer=lambda m: json.loads(m.decode('utf-8')))
event_id=None
try:
    with psycopg2.connect(
        host="localhost",
        database="incident_db", user="postgres" , password="password") as conn:
        with conn.cursor() as cursor:
            for message in consumer:
                event = message.value
                print(f"Received event: {event}")
                cursor.execute(
                    "INSERT INTO incidents (event_type, resource_name, fingerprint, raw_event, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (event["type"], event["resource"], event["fingerprint"], json.dumps(event), event["timestamp"]) 
                )
                row=cursor.fetchone()
                if row:
                    event_id=row[0]
                conn.commit()
except (Exception, psycopg2.DatabaseError) as error:
    print(error)