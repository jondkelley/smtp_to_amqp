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
import collections
import configparser
import email
import logging
import logging as loggingg
import mimetypes
import pickle

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

async def worker_mysql_writeout(loop, eml, payload):
    """
    write event log to mysql
    """
    pass

async def worker_redis_writeout(loop, eml, payload):
    """
    write decoded attachments to redis
    """
    logging.warning(eml.keys())
    sqlmessage = {}
    sqlmessage['campaign'] = payload['data']['campaign']
    sqlmessage['domain'] = payload['data']['domain']
    sqlmessage['identity'] = payload['data']['identity']
    sqlmessage['uuid'] = payload['data']['tid']
    # Fetch attachments
    ALLOW_EXT = config['amqpworker'].get('allowed_attachment_extensions', '').split(",")
    if ALLOW_EXT == '':
        ALLOW_EXT = []
    DISALLOW_EXT = config['amqpworker'].get('deny_attachment_extensions', '').split(",")
    if DISALLOW_EXT == '':
        DISALLOW_EXT = []

    counter = 0
    redismessage = {}
    redismessage['t_uid'] = payload['data']['tid']
    redismessage['from'] = payload['data']['from']
    redismessage['tos'] = payload['data']['tos']
    redismessage['from'] = payload['data']['from']
    redismessage['raw_files'] = {}
    for part in eml.walk():
        counter += 1
        # multipart/* are just containers
        if part.get_content_maintype() == 'multipart':
            continue
        else:
            logging.warning("Content type not multipart")

        redismessage['subject'] = eml['subject']
        # Applications should really sanitize the given filename so that an
        # email message can't be used to overwrite important files
        filename = part.get_filename()
        if not filename:
            #ext = mimetypes.guess_extension(part.get_content_type())
            # Use a generic bag-of-bits extension
            ext = '.txt'
            filename = 'part-%03d%s' % (counter, ext)
        realext = str(filename).split('.')[-1]
        payload=part.get_payload(decode=True)
        allow_file = False
        if (len(ALLOW_EXT) == 0) or (realext in ALLOW_EXT):
            allow_file = True
        if (len(DISALLOW_EXT) > 0) and (realext in DISALLOW_EXT):
            allow_file = False
        if allow_file:
            if filename == "part-001.txt":
                redismessage['txt'] = payload
            elif filename == "part-002.txt":
                redismessage['html'] = payload
            else:
                print("including attachment {}".format(filename))
                redismessage['raw_files'][filename] = payload
        else:
            print("dropping prohibited attachment {}".format(filename))
            #logger.info()
            counter = counter - 1
        redismessage['original_content'] = str(eml)
        logging.error(redismessage)

async def process_inbound_message(payload, options, sleep=0, *, loop):
    """
    Initially validates payload and transfers to worker functions
    """
    await asyncio.sleep(sleep, loop=loop)
    try:
        payload = pickle.loads(payload)
        payload['envelope']
    except Exception as e:
        logging.error("Discarding envelope, invalid format/decoding exception: {}".format(e))
        return

    if payload['envelope'] > 0:
        t_uid = payload['data']['tid']
        fro = payload['data']['from']
        to = str(payload['data']['tos']).replace('[', '').replace(']', '').replace('\'', '')
        utf = payload['data']['utf8']
        logging.warning("New amqp message {} from mail server utf8={} from={} to={}".format(t_uid, utf, fro, to,))

        eml = email.message_from_string(payload['data']['original_content'])

        # handles the administrative functions of message processing
        await worker_redis_writeout(loop, eml, payload)
        await worker_mysql_writeout(loop, eml, payload)

async def forever(*, loop, amqp_url, amqp_queue_name):
    """"
    paginate off amqp and process tasks
    """
    amqp_url = amqp_url
    # i.e. 'amqp://guest:guest@127.0.0.1:55672//'
    queue_kwargs = {
        'durable': True,
    }
    amqp_kwargs = {}  # https://aioamqp.readthedocs.io/en/latest/api.html#aioamqp.connect

    consumer = Consumer(
        amqp_url,
        partial(process_inbound_message, loop=loop, sleep=0),
        amqp_queue_name,
        queue_kwargs=queue_kwargs,
        amqp_kwargs=amqp_kwargs,
        loop=loop,
    )
    await consumer.scale(int(config['amqpworker'].get('threads', 8)))
    await consumer.join()  # wait for rabbitmq queue is empty and all local messages are processed
    asyncio.sleep(0.5)
    # ----below----- cause consumer to exit once to bottom of queue
    # consumer.close()
    # await consumer.wait_closed()
    # consumer.close()
    # await consumer.wait_closed()

def entrypoint():
    loop = asyncio.get_event_loop()
    amqp_url = config['amqpworker']['aqmp_backend_url']
    amqp_queue = config['amqpworker']['amqp_backend_queue']
    loop.run_until_complete(forever(loop=loop, amqp_url=amqp_url, amqp_queue_name=amqp_queue))
    loop.run_forever()

if __name__ == '__main__':
    entrypoint()
