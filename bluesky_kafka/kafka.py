import asyncio

from kafka import KafkaProducer, KafkaConsumer
from bluesky.run_engine import Dispatcher
import pickle

from bluesky.callbacks.core import CallbackBase

from bluesky.run_engine import Dispatcher, DocumentNames

import time


class Producer:
    """
    A callback that publishes documents to kafka.

    Parameters
    ----------
    bootstrap_servers: list
        list of servers the brokers run on
    topic: str
        topic to push to
    logger : Logger instance
        A logger instance to log output to.
        Logs are outputted only if logging.DEBUG level or higher are set
    timeout: int, optional
        The amount of time to timeout if a message is not sent

    Example
    -------
    >>> producer = Producer(bootstrap_servers=['localhost:9092'], topic='analysis')
    """
    def __init__(self, bootstrap_servers, topic, serializer=None, logger=None, timeout=2):
        self.logger = logger
        if serializer is None:
            self.serializer = pickle.dumps
        self._publisher = KafkaProducer(bootstrap_servers=bootstrap_servers)
        self._topic = topic
        self._timeout = timeout

    def __call__(self, name, doc):
        if self.logger is not None:
            self.logger.debug("Received a message from %s", name)
        message = b' '.join([name.encode(), self.serializer(doc)])
        future = self._publisher.send(self._topic, message)
        # NOTE: we have to wait on sending. Add max timeout and check for
        # delivery
        result = future.get(timeout=self._timeout)
        if not result.succeeded():
            raise result.exception



class ConsumerDispatcher(Dispatcher):
    """
    Dispatch documents received over the network from a kafka message bus.

    Parameters
    ----------
    bootstrap_servers : list
        list of kafka servers in hostname:port format
    topic : str
        the topic to listen to
    loop : asyncio event loop, optional
    logger : Logger instance
        A logger instance to log output to.
        Logs are outputted only if logging.DEBUG level or higher are set

    Example
    -------

    Print all documents generated by remote RunEngines.

    >>> d = ConsumerDispatcher(bootstrap_servers=['localhost:5568'], 'analysis')
    >>> d.subscribe(print)
    >>> d.start()  # runs until interrupted
    """
    # TODO : Should we add runengine id and filter by that?
    def __init__(self, bootstrap_servers, topic, loop=None, deserializer=None,
                 logger=None):
        self.logger = logger
        if deserializer is None:
            self.deserializer = pickle.loads 
        self._topic = topic
        self._consumer = KafkaConsumer(topic, bootstrap_servers=bootstrap_servers)
        # create an event loop in asyncio
        if loop is None:
            loop = asyncio.new_event_loop()
        self.loop = loop
        self.poll_time = .5 # 1 second

        super().__init__()

    # kafka doesn't have asyncio methods, so we poll and sleep
    async def _poll(self):
        while True:
            message = self._consumer.poll()  # 1 sec timeout
            if len(message):
                if self.logger is not None:
                    self.logger.debug("KafkaProducer : Getting a consumer message")
                for key, crecords in message.items():
                    if key.topic == self._topic:
                        for crecord in crecords:
                            message = crecord.value
                            if self.logger is not None:
                                self.logger.debug("Message : %s", message)
                            name, doc = message.split(b' ', maxsplit=1)
                            if self.logger is not None:
                                self.logger.debug("name: %s", name)
                            name = name.decode()
                            doc = self.deserializer(doc)
                            self.loop.call_soon(self.process, DocumentNames[name], doc)
            await asyncio.sleep(self.poll_time)

    def start(self):
        try:
            self._task = self.loop.create_task(self._poll())
            self.loop.run_forever()
        except:
            self.stop()
            raise

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self.loop.stop()
        self._task = None
