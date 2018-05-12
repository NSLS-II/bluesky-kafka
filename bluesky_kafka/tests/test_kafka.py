import time
from kafka import KafkaProducer, KafkaConsumer
import threading
import os

import pickle

brokers = os.environ.get("BROKERS")
receive_messages = list()
TOPIC = 'test'

producer = KafkaProducer(bootstrap_servers=brokers)
consumer = KafkaConsumer(bootstrap_servers=brokers)
consumer.subscribe(TOPIC)


def get_messages():
    for receive_message in consumer:
        res = pickle.loads(receive_message.value)
        receive_messages.append(res)

th = threading.Thread(target=get_messages)
th.daemon = True
th.start()

send_messages = [
"test",
"test2",
]

for send_message in send_messages:
    future = producer.send(topic=TOPIC, value=pickle.dumps(send_message))
    future.get(60)
# give a short delay
time.sleep(1)

assert len(send_messages) == len(receive_messages)
for send_message, receive_message in zip(send_messages, receive_messages):
    assert send_message == receive_message
