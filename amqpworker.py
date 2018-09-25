#!/usr/bin/env python3
# FreeBSD License
# Copyright 2018 Jonathan Kelley
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those of the authors and should not be interpreted as representing official policies, either expressed or implied, of the author.

from aioamqp_consumer import Consumer, Producer
from datetime import datetime, timezone
from functools import partial
import asyncio
import bson
import collections
import configparser
import email
import logging
import logging as loggingg

__version__ = "0.0.1"
__author__ = "Jonathan Kelley, jonkelley@gmail.com"
__copyright__ = "2018 Jonathan Kelley. The FreeBSD Copyright"

config = configparser.ConfigParser()
config.read('config/ingestapi.ini')

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

def entrypoint():
    loop = asyncio.get_event_loop()
    amqp_url = config['amqpworker']['aqmp_backend_url']
    loop.run_until_complete(infinite(loop=loop, amqp_url=amqp_url))
    loop.close()

if __name__ == '__main__':
    entrypoint()
