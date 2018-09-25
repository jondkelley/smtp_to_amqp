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

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage
from aiosmtpd.smtp import SMTP, syntax
from asyncio import coroutine
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from uuid import uuid4
import aioamqp
import asyncio
import collections
import configparser
import email
import logging
import logging as loggingg
import pickle
import re

# Test the server with this (python2) tool https://raw.githubusercontent.com/turbodog/python-smtp-mail-sending-tester/master/smtptest.py

__version__ = "0.1.0"
__metarealease__ = "alpha"
__author__ = "Jonathan Kelley, jonkelley@gmail.com"
__copyright__ = "2018 Jonathan Kelley. The FreeBSD Copyright"

config = configparser.ConfigParser()
config.read('config/ingestapi.ini')
class AnsiColor():
    """
    life is better in color
    """
    header = '\033[95m'
    blue = '\033[1;94m'
    green = '\033[1;92m'
    yellow = '\033[93m'
    red = '\033[91m'
    end = '\033[0m'
    bold = '\033[1m'
    magenta = '\033[35m'
    underline = '\033[4m'

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
            amqp_host = config['smtpd']['amqp_host']
            amqp_port = config['smtpd']['amqp_port']
            transport, protocol = await aioamqp.connect(amqp_host, amqp_port)
            self.amqpchannel = await protocol.channel()
        except aioamqp.AmqpClosedConnection as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True
        except Exception as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True

        try:
            logging.warning("client HELO testing AMQP connection")
            await self.amqpchannel.queue(config['smtpd']['amqp_worker_queue'], durable=True)
            message = {"envelope": 0}
            message = pickle.dumps(message)
            await self.amqpchannel.basic_publish(payload=message, exchange_name='',
                routing_key=config['smtpd']['amqp_worker_queue'], properties={ 'delivery_mode': 2 },
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
        self.envelope.t_message_id = str(uuid4()).split('-', 2)[2].replace('-', '')
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
            amqp_host = config['smtpd']['amqp_host']
            amqp_port = config['smtpd']['amqp_port']
            transport, protocol = await aioamqp.connect(amqp_host, amqp_port)
            self.amqpchannel = await protocol.channel()
        except aioamqp.AmqpClosedConnection as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True
        except Exception as e:
            logging.error(generic_amqp_error.format(arg, e))
            fail = True

        try:
            logging.warning("client EHLO testing AMQP connection")
            await self.amqpchannel.queue(config['smtpd']['amqp_worker_queue'], durable=True)
            message = {"envelope": 0}
            message = pickle.dumps(message)
            await self.amqpchannel.basic_publish(payload=message, exchange_name='',
                routing_key=config['smtpd']['amqp_worker_queue'], properties={ 'delivery_mode': 2 },
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
        default_ident = "SMTP Digester v{} ({})".format(_ver, _meta)

        datalimit = int(config['smtpd']['message_size_limit'])
        decodedata = config['smtpd']['decode_data']
        enablesmtputf8 = config['smtpd']['enable_SMTPUTF8']
        myident = config['smtpd'].get('banner', default_ident)
        smtp = SMTPOverload(self.handler, data_size_limit=datalimit, decode_data=decodedata, enable_SMTPUTF8=self.enable_SMTPUTF8, ident=myident)
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
        mailtos = str(envelope.rcpt_tos).split('[')[1].split(']')[0].replace('\'', '').replace(',', ';')
        logging.warning("new message {} from={} tos={}".format(envelope.t_message_id, envelope.mail_from, mailtos))
        await self.digest_message(message, envelope)
        logging.warning("Sent peer: Msg 250 OK {} accepted for delivery".format(envelope.t_message_id))
        logging.warning("Finished processing {}".format(envelope.t_message_id))
        return '250 OK message {} accepted for delivery'.format(envelope.t_message_id)

    async def digest_message(self, message, envelope):
        """
        perform action on any elements of the incoming email
        """
        # allow auxillary publisher queues
        auxqueues = config['smtpd'].get('amqp_aux_queues', False)
        msg = None
        campaigns = config['smtpd'].get('campaigns')
        for recipient in envelope.rcpt_tos:
            logging.warning("ingested message {} recipient={}".format(envelope.t_message_id, recipient))
            campaign_match = False
            for campaign in campaigns:
                try:
                    rcptprefix = recipient.split("-")[0].lower()
                    campaign_match = True
                except:
                    rcptprefix = ""
                if campaign == rcptprefix:
                    try:
                        msg = email.message_from_bytes(envelope.original_content)
                    except Exception as e:
                        logging.error("error decoding message, message {} was lost! exception: {}".format(envelope.t_message_id, e))
                else:
                    continue

        recipient = re.search(r'[\w\.-]+@[\w\.-]+', envelope.rcpt_tos[0]).group(0)
        domain = recipient.split('@')[-1].lower()
        identity = recipient.split('@')[0].split('-')[-1]
        campaign = recipient.split('@')[0].split('-')[0].lower()

        logging.warning("digested message {} campaign={} domain={} identity={}".format(envelope.t_message_id, campaign,  domain, identity))

        generic_amqp_error = "AMQP issue, message {} was destroyed in transit, exception: {}"
        try:
            amqp_host = config['smtpd']['amqp_host']
            amqp_port = config['smtpd']['amqp_port']
            transport, protocol = await aioamqp.connect(amqp_host, amqp_port)
            self.amqpchannel = await protocol.channel()
        except aioamqp.AmqpClosedConnection as e:
            logging.error(generic_amqp_error.format(envelope.t_message_id, e))
        except Exception as e:
            logging.error(generic_amqp_error.format(envelope.t_message_id, e))
        try:
            await self.amqpchannel.queue(config['smtpd']['amqp_worker_queue'], durable=True)
        except Exception as e:
            logging.error("Error setting up amqp channel, exception: {}".format(e))
        if auxqueues:
            for auxqueue in auxqueues.split(","):
                try:
                    await self.amqpchannel.queue(auxqueue, durable=True)
                except Exception as e:
                    logging.error("Error setting up amqp channel, exception: {}".format(e))
        logging.info("message length={}".format(len(envelope.original_content)))

        a, b, x  = __version__.split(".")
        amqp_version = (a, b)
        # only include major, minor version as contract identifier (not build)
        amqp_envelope = {
            "envelope": 1,
            "v": amqp_version,
            "datetimes_utc": {
                "smtpserver_processed": datetime.utcnow()
            },
            "data":
                {
                    "tid": str(envelope.t_message_id),
                    "from": str(envelope.mail_from),
                    "tos": list(envelope.rcpt_tos),
                    "rcpt_opts": str(envelope.rcpt_options),
                    "utf8": str(envelope.smtp_utf8),
                    "campaign": str(campaign),
                    "identity": str(identity),
                    "domain": str(domain),
                    "original_content": str(envelope.original_content)
                }
        }
        amqp_envelope = pickle.dumps(amqp_envelope)

        try:
            await self.amqpchannel.basic_publish(
                payload=amqp_envelope,
                exchange_name='',
                routing_key=config['smtpd']['amqp_worker_queue'],
                properties={
                    'delivery_mode': 2,
                },
            )
        except Exception as e:
            logging.error("Error writing to amqp channel, exception: {}".format(e))
        if auxqueues:
            for auxqueue in auxqueues.split(","):
                logging.info("Duplicating amqp message {} to auxillary queue {}".format(envelope.t_message_id, auxqueue))
                try:
                    await self.amqpchannel.basic_publish(
                        payload=amqp_envelope,
                        exchange_name='',
                        routing_key=auxqueue,
                        properties={
                            'delivery_mode': 2,
                        },
                    )
                except Exception as e:
                    logging.error("Error writing to amqp channel, exception: {}".format(e))
        logging.warning("AMQP (COMMIT OK) generated bson of message {}".format(envelope.t_message_id))
        protocol.close()
        transport.close()

async def smtp_main(loop):
    """
    smtp server
    """
    logging.info("smtp_main thread")
    list_host = config['smtpd'].get('listen_host', '127.0.0.1')
    list_port = config['smtpd'].get('listen_port', '8025')
    controller = SMTPControllerOverload(MessageOverload(), hostname=list_host, port=list_port)
    try:
        logging.warning("controller is listening on {}:{}".format(list_host, list_port))
        controller.start()
    except OSError as e:
        logging.critical("main thread crashed, exception {}".format(e))
    except Exception as e:
        logging.critical("main thread crashed, exception {}".format(e))

@coroutine
def loop_main():
    """
    Always keep a standby thread
    """
    logging.info("loop main_thread")
    while(True):
        logging.debug("Tick")
        yield from asyncio.sleep(10)

def configure_logging():
    logpath = config['smtpd']['log_file']
    format=('{blue1}%(asctime)s '
            '{red1}%(filename)s:%(lineno)d '
            '{yel1}%(levelname)s '
            '{gre1}%(funcName)s() '
            '{res}%(message)s').format(blue1=AnsiColor.blue, red1=AnsiColor.red, yel1=AnsiColor.yellow, res=AnsiColor.end, gre1=AnsiColor.magenta)
    format1=('%(asctime)s '
            '%(filename)s:%(lineno)d '
            '%(levelname)s '
            '%(funcName)s() '
            '%(message)s')
    logFormatter = loggingg.Formatter(format)
    logFormatterfile = loggingg.Formatter(format1)
    logging = loggingg.getLogger()
    logging.setLevel(loggingg.INFO)

    fileHandler = loggingg.FileHandler(logpath)
    fileHandler.setFormatter(logFormatterfile)
    logging.addHandler(fileHandler)

    consoleHandler = loggingg.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logging.addHandler(consoleHandler)

def entrypoint():
    configure_logging()
    logging.warning("Starting asyncio SMTP...")
    loop = asyncio.get_event_loop()
    tasks = [
        asyncio.Task(smtp_main(loop=loop)),
        asyncio.Task(loop_main()),
        ]

    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    entrypoint()
