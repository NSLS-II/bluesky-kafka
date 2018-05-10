The bluesky-kafka module. Meant to use with databroker.

Usage:
```py3
from bluesky_kafka import Producer, ConsumerDispatcher
from threading import Thread

from databroker import Broker

db = Broker.named("chx")

docs = db[-2].documents()

prod = Producer(bootstrap_servers=['localhost:9092'], topic="test")
consumer = ConsumerDispatcher(bootstrap_servers=['localhost:9092'], topic="test")

def printdoc(name, doc):
    print("Got a document with name {}".format(name))
    print("Contents : {}".format(doc))

consumer.subscribe(printdoc)

print("starting consumer thread")
th = Thread(target=consumer.start)
# so we can quit ipython without waiting on thread
th.daemon=True
th.start()
import time
time.sleep(1)
print('done')


for nds in docs:
    print("sending {} document".format(nds[0]))
    prod(*nds)
```
