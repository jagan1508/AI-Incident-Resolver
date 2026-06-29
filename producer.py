from kafka import KafkaProducer
import json 
import time 

events = [
    {"type": "pod_crash", "resource": "checkout-svc", "fingerprint": "pod_crash:checkout-svc",},
    {"type": "pod_crash", "resource": "checkout-svc", "fingerprint": "pod_crash:checkout-svc"},
    {"type": "cpu_spike", "resource": "payment-svc", "fingerprint": "cpu_spike:payment-svc"},
]

producer = KafkaProducer(bootstrap_servers='localhost:9092',value_serializer=lambda v: json.dumps(v).encode('utf-8'))
for event in events:
    event["timestamp"] = time.ctime(time.time())
    producer.send('demo', event)
    time.sleep(5)
producer.flush()