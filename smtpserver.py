#!/usr/bin/env python3
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage
from aiosmtpd.smtp import SMTP, syntax
from asyncio import coroutine
from datetime import datetime, timezone
import asyncio
import logging
import uuid
import logging
import aio_pika
import threading
import aioamqp
import aiohttp
import json

__version__ = "0.0.1"
__metarealease__ = "alpha"

class SMTPOverload(SMTP):
    """
    overloads homebrew smtp commands
    """

    @syntax('HELO hostname')
    async def smtp_HELO(self, arg):
        """
        validate amqp availability before processing email
        """
        generic_amqp_error = "AMQP connection issue, message deferred from {} exception: {}"
        fail = False
        self.amqpchannel = None
        try:
            transport, protocol = await aioamqp.connect('127.0.0.1', 55672)
            self.amqpchannel = await protocol.channel()
        except aioamqp.AmqpClosedConnection as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True
        except Exception as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True

        try:
            await self.amqpchannel.queue('ingestqueue', durable=True)
            message = {"h": 0}
            message = json.dumps(message)
            await self.amqpchannel.basic_publish(
                payload=message,
                exchange_name='',
                routing_key='ingestqueue',
                properties={
                    'delivery_mode': 2,
                },
            )
            logging.debug("Sent message {}".format(message))
            await protocol.close()
            await transport.close()
        except:
            pass
        if fail:
            await self.push('421 Cannot process email at this time')
            return
        hostport = "{} port {}".format(self.session.peer[0], self.session.peer[1])
        logging.info("smtp HELO from peer {}".format(hostport))
        logging.info("smtp HELO from peer {}".format(self.session.peer))
        await super().smtp_HELO(arg)


    @syntax('MAIL FROM: <address>', extended=' [SP <mail-parameters>]')
    async def smtp_MAIL(self, arg):
        """
        overload to add uuid to envelope
        """
        self.envelope.t_message_id = str(uuid.uuid4()).split('-', 2)[2].replace('-', '')
        await super().smtp_MAIL(arg)

    @syntax('EHLO hostname')
    async def smtp_EHLO(self, arg):
        """
        validate amqp availability before processing email
        """
        await super().smtp_EHLO(arg)
        generic_amqp_error = "AMQP connection issue, message deferred from {} exception: {}"
        fail = False
        self.amqpchannel = None
        try:
            transport, protocol = await aioamqp.connect('127.0.0.1', 55672)
            self.amqpchannel = await protocol.channel()
        except aioamqp.AmqpClosedConnection as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True
        except Exception as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True

        try:
            await self.amqpchannel.queue('ingestqueue', durable=True)
            message = {"h": 0}
            message = json.dumps(message)
            await self.amqpchannel.basic_publish(
                payload=message,
                exchange_name='',
                routing_key='ingestqueue',
                properties={
                    'delivery_mode': 2,
                },
            )
            logging.debug("Sent message {}".format(message))
            await protocol.close()
            await transport.close()
        except:
            pass
        if fail:
            await self.push('421 Cannot process email at this time')
            return
        hostport = "{} port {}".format(self.session.peer[0], self.session.peer[1])
        logging.info("smtp EHLO from peer {}".format(hostport))

    @syntax('TEST value')
    async def smtp_TEST(self, value):
        """
        smtp test command
        """
        if not 'alpha' in __metarealease__:
            help = "501 Command not implemented"
            await self.push(help)
            return
        elif not value:
            await self.push('501 Syntax: TEST value')
            return

        prefix="211"
        if value == ".":
            help = ("{prefix} it works\n"
                    "{prefix} congratulations").format(prefix=prefix)
            await self.push(help)
            return
        elif value == "value":
            await self.push("501 LOL nice try though")
            return
        elif value == "die":
            logging.info("smtp test die issued; simulating hard crash".format(prefix=prefix))
            help = ("503 simulate hard process crash\n"
                    "503 thanks for all the fish").format(prefix=prefix)
            await self.push(help)
            exit(0)
        else:
            await self.push('501 invalid test code')
            return
        status = await self._call_handler_hook('TEST', value)
        await self.push(status)

class SMTPControllerOverload(Controller):
    """
    overloads custom smtp controller functionality
    """
    def factory(self):
        """
        overload MySMTP and ident=
        """
        _ver = __version__
        _meta = __metarealease__.upper()
        smtp = SMTPOverload(self.handler, enable_SMTPUTF8=self.enable_SMTPUTF8, ident="SMTP Digester v{} ({})".format(_ver, _meta))
        return smtp

class MessageOverload(AsyncMessage):
    """
    overloads attributes to get active access with envelopes / incoming data
    you can proxy, store or forward if you wanna
    """
    def __init__(self, message_class=None, *, loop=None):
        super().__init__(message_class)
        self.loop = loop or asyncio.get_event_loop()

    async def handle_DATA(self, server, session, envelope):

        message = self.prepare_message(session, envelope)
        await self.handle_message(message, envelope)
        mailtos = str(envelope.rcpt_tos).split('[')[1].split(']')[0].replace('\'', '').replace(',', ';')
        logging.info("accepted message from={} tos={} t_message_id={}".format(envelope.mail_from, mailtos, envelope.t_message_id))
        return '250 OK message {} accepted for ingest'.format(envelope.t_message_id)

    async def handle_message(self, message, envelope):
        """
        perform action on any elements of the incoming email
        """

        generic_amqp_error = "AMQP issue, message {} was destroyed in transit, exception: {}"
        try:
            transport, protocol = await aioamqp.connect('127.0.0.1', 55672)
            self.amqpchannel = await protocol.channel()
        except aioamqp.AmqpClosedConnection as e:
            logging.error(generic_amqp_error.format(envelope.t_message_id, e))
        except Exception as e:
            logging.error(generic_amqp_error.format(envelope.t_message_id, e))
        await self.amqpchannel.queue('ingestqueue', durable=True)

        amqp_envelope = {
            "h": 1,
            "m": {
                    "time_arrival": {
                        "amqp": {0: datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(), 1: datetime.now().timestamp()}
                    }
                },
            "d": {
                    "tid": envelope.t_message_id, "msg": str(message), "from": str(envelope.mail_from),
                    "tos": list(envelope.rcpt_tos), "rcpt_opts": str(envelope.rcpt_options),
                    "utf8": str(envelope.smtp_utf8)
                }
            }
        amqp_envelope = json.dumps(amqp_envelope) + "\n\n"

        await self.amqpchannel.basic_publish(
            payload=amqp_envelope,
            exchange_name='',
            routing_key='ingestqueue',
            properties={
                'delivery_mode': 2,
            },
        )
        logging.info("amqp message COMMIT t_message_id={}".format(envelope.t_message_id))
        protocol.close()
        transport.close()


async def smtp_main(loop):
    """
    smtp server
    """
    logging.info("smtp_main thread")
    control = SMTPControllerOverload(MessageOverload(), hostname='', port=8025)
    control.start()

async def bmain(loop):
    """
    amqp connection client
    """
    logging.info("An AMQP client has some blocking in b(main)")
    connection = await aio_pika.connect_robust("amqp://guest:guest@127.0.0.1:33323", loop=loop)
    queue_name = "test_queue"

    # Creating channel
    try:
        channel = await connection.channel()    # type: aio_pika.Channel

    # Declaring queue
        queue = await channel.declare_queue(queue_name, auto_delete=True)   # type: aio_pika.Queue

        async for message in queue:
            with message.process():
                print(message.body)

                if queue.name in message.body.decode():
                    break
    except RuntimeError:
        logging.info("smtp amqp server socket collapsed, messages may be lost in-transit")

@coroutine
def loop_main():
    """
    Always keep a standby thread
    """
    logging.info("loop main_thread")
    while True:
        yield from asyncio.sleep(5)

async def fetch(session, url):
    """
    loads a http session with url
    """
    async with session.get(url, verify_ssl=False) as response:
        return await response.text()

async def dmain(url):
    """
    url expensive blocking work test
    """
    async with aiohttp.ClientSession() as session:
        for i in range(99999999):
            print(i)
            html = await fetch(session, url)
            print(html)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    tasks = [
        asyncio.Task(smtp_main(loop=loop)),
        #asyncio.Task(bmain(loop=loop)),
        asyncio.Task(loop_main()),
        #asyncio.Task(dmain(url='http://192.168.0.1'))
        ]

    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        pass
