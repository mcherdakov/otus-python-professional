import datetime
import hashlib

import pytest
from app import consts
from app.api import check_auth
from app.methods import MethodRequest


class TestAuth:
    @staticmethod
    def _set_valid_auth(request):
        if request.get('login') == consts.ADMIN_LOGIN:
            hash_string = (
                datetime.datetime.now().strftime('%Y%m%d%H') +
                consts.ADMIN_SALT
            ).encode('utf-8')
            request['token'] = hashlib.sha512(hash_string).hexdigest()
        else:
            msg = (
                request.get('account', '') +
                request.get('login', '') +
                consts.SALT
            )
            msg = msg.encode('utf-8')
            request['token'] = hashlib.sha512(msg).hexdigest()

    @pytest.mark.parametrize(
        'request_body',
        (
            {
                'account': 'horns&hoofs',
                'login': 'h&f',
                'method': 'online_score',
                'token': '',
                'arguments': {},
            },
            {
                'account': 'horns&hoofs',
                'login': 'h&f',
                'method': 'online_score',
                'token': 'sdd',
                'arguments': {},
            },
            {
                'account': 'horns&hoofs',
                'login': 'admin',
                'method': 'online_score',
                'token': '', 'arguments': {},
            },
        )
    )
    def test_bad_auth(self, request_body):
        method_request = MethodRequest(request_body)
        assert not check_auth(method_request)

    @pytest.mark.parametrize(
        'request_body',
        (
            {
                'account': 'admin',
                'login': 'admin',
                'method': 'online_score',
                'arguments': {},
            },
            {
                'account': 'test',
                'login': 'test',
                'method': 'online_score',
                'arguments': {},
            },

        )
    )
    def test_valid_auth(self, request_body):
        self._set_valid_auth(request_body)
        method_request = MethodRequest(request_body)
        assert check_auth(method_request)
