#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import hashlib
import json
import logging
import os
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser

from app import consts
from app.fields import ValidationError
from app.methods import MethodNotFound, MethodRequest, process_method_request
from app.store import RedisStore


def check_auth(request: MethodRequest) -> bool:
    if request.is_admin:
        hash_string = (
            datetime.datetime.now().strftime('%Y%m%d%H') +
            consts.ADMIN_SALT
        )
    else:
        account = request.account if request.account is not None else ''
        login = request.login if request.login is not None else ''
        hash_string = account + login + consts.SALT

    digest = hashlib.sha512(hash_string.encode('utf-8')).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    method_request = MethodRequest(request['body'])
    try:
        method_request.validate()
    except ValidationError as e:
        return str(e), consts.INVALID_REQUEST

    if not check_auth(method_request):
        return None, consts.FORBIDDEN

    try:
        return process_method_request(method_request, ctx, store), consts.OK
    except ValidationError as e:
        return str(e), consts.INVALID_REQUEST
    except MethodNotFound:
        return None, consts.INVALID_REQUEST


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        'method': method_handler
    }
    store = RedisStore(
        host=os.environ.get('REDIS_HOST', 'redis'),
        port=int(os.environ.get('REDIS_PORT', '6379')),
        timeout=10,
    )

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, consts.OK
        context = {'request_id': self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except Exception as e:
            print(e)
            code = consts.BAD_REQUEST

        if request:
            path = self.path.strip('/')
            logging.info(
                '%s: %s %s' % (
                    self.path,
                    data_string,
                    context['request_id'],
                )
            )
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {'body': request, 'headers': self.headers},
                        context,
                        self.store,
                    )
                except Exception as e:
                    logging.exception('Unexpected error: %s' % e)
                    code = consts.INTERNAL_ERROR
            else:
                code = consts.NOT_FOUND

        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        if code not in consts.ERRORS:
            r = {'response': response, 'code': code}
        else:
            r = {
                'error': response or consts.ERRORS.get(code, 'Unknown Error'),
                'code': code
            }
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == '__main__':
    op = OptionParser()
    op.add_option('-p', '--port', action='store', type=int, default=8080)
    op.add_option('-l', '--log', action='store', default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S'
    )
    server = HTTPServer(('0.0.0.0', opts.port), MainHTTPHandler)
    logging.info('Starting server at %s' % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
