#!/usr/bin/env python3

import asyncio
from functools import partial
from aioamqp_consumer import Consumer, Producer
import configparser

class AttachmentRedisObject:
    """
    amqp message format for attachments
    """
    def __init__():
        self.expiration = None
        self.content_type = None
        self.content = None

async def digest_email(payload, options, sleep=0, *, loop):
    await asyncio.sleep(sleep, loop=loop)
    # get domain,  regex, etc applied
    # if smarthost
    # if amqp forward
    # if http forward
    print(payload)

async def task(payload, options, sleep=0, *, loop):
    await asyncio.sleep(sleep, loop=loop)
    print(payload)

async def infinite(*, loop, amqp_url):
    """"
    paginate off amqp and process tasks
    """
    amqp_url = amqp_url
    # i.e. 'amqp://guest:guest@127.0.0.1:55672//'
    amqp_queue = 'ingestqueue'
    queue_kwargs = {
        'durable': True,
    }
    amqp_kwargs = {}  # https://aioamqp.readthedocs.io/en/latest/api.html#aioamqp.connect

    consumer = Consumer(
        amqp_url,
        partial(task, loop=loop, sleep=0),
        amqp_queue,
        queue_kwargs=queue_kwargs,
        amqp_kwargs=amqp_kwargs,
        loop=loop,
    )
    #await consumer.scale(20)  # scale up to 20 background coroutines
    await consumer.scale(8)  # downscale to 5 background coroutines
    await consumer.join()  # wait for rabbitmq queue is empty and all local messages are processed
    consumer.close()
    await consumer.wait_closed()

config = configparser.ConfigParser()
config.read('config/ingestapi.ini')
loop = asyncio.get_event_loop()
amqp_url = config['amqpworker']['aqmp_backend_url']
loop.run_until_complete(infinite(loop=loop, amqp_url=amqp_url))
loop.close()
