#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG, ROUTER_FRONTEND, ROUTER_GATHERER, STORAGE_ADDR, \
    ROUTER_PUBLISHER, CTRL_ADDR
import time
import os.path

from pprint import pprint
import zmq
from zmq.eventloop import ioloop
import sys
import json
import time


class Router(object):

    def __init__(self, frontend=ROUTER_FRONTEND, publisher=ROUTER_PUBLISHER, storage=STORAGE_ADDR,
                 logger=logging.getLogger(__name__), **kwargs):
        self.logger = logger

        self.context = zmq.Context.instance()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.storage = self.context.socket(zmq.DEALER)
        self.publisher = self.context.socket(zmq.PUB)
        self.ctrl = self.context.socket(zmq.REP)

        self.poller = zmq.Poller()

        self.ctrl.bind(CTRL_ADDR)
        self.frontend.bind(frontend)
        self.publisher.bind(publisher)
        self.storage.bind(storage)

    def auth(self, token):
        if not token:
            return 0
        return 1

    def handle_ctrl(self, s, e):
        self.logger.debug('ctrl msg recieved')
        id, mtype, data = s.recv_multipart()

        self.ctrl.send_multipart(['router', 'ack', str(time.time())])

    def handle_message(self, s, e):
        self.logger.debug('message received')
        m = s.recv_multipart()

        id, null, token, mtype, data = m
        self.logger.debug("mtype: {0}".format(mtype))

        if self.auth(token):
            handler = getattr(self, "handle_" + mtype)
            rv = handler(token, data)
        else:
            rv = json.dumps({
                "status": "failed",
                "data": "unauthorized"
            })

        self.frontend.send_multipart([id, '', mtype, rv])

    def handle_ping(self, data):
        rv = {
            "status": "success",
            "data": str(time.time())
        }
        return json.dumps(rv)

    def handle_write(self, data):
        rv = {
            "status": "failed",
            "data": str(time.time())
        }
        return json.dumps(rv)

    def handle_search(self, token, data):
        self.storage.send_multipart(['search', token, data])
        m = self.storage.recv()
        rv = {
            "status": "success",
            "data": m,
        }
        return json.dumps(rv)

    def handle_submission(self, token, data):
        self.storage.send_multipart(['submission', token, data])
        m = self.storage.recv()
        rv = {
            "status": "success",
            "data": m,
        }
        return json.dumps(rv)

    def run(self):
        self.logger.debug('starting loop')
        loop = ioloop.IOLoop.instance()
        loop.add_handler(self.frontend, self.handle_message, zmq.POLLIN)
        loop.add_handler(self.ctrl, self.handle_ctrl, zmq.POLLIN)
        loop.start()


def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-router -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-router'
    )

    p.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    p.add_argument('-d', '--debug', dest='debug', action="store_true")

    p.add_argument('--frontend', dest='listen', help='address to listen on', default=ROUTER_FRONTEND)
    p.add_argument('--publish', dest='publish', help='address to publish on', default=ROUTER_PUBLISHER)
    p.add_argument("--storage", dest="storage", help="specify a storage address", default=STORAGE_ADDR)

    p.add_argument("--config", dest="config", help="specify a configuration file [default: %(default)s]",
                        default=os.path.join(os.path.expanduser("~"), DEFAULT_CONFIG))


    args = p.parse_args()

    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)
    logger = logging.getLogger(__name__)

    options = vars(args)

    r = Router(logger=logger)
    logger.info('staring router...')
    try:
        r.run()
    except KeyboardInterrupt:
        logger.info('shutting down...')
        sys.exit()



if __name__ == "__main__":
    main()
