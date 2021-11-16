import hashlib
import json

import pytest
from app import consts
from app.api import method_handler
from app.store import RedisStore
from redis.exceptions import ConnectionError


@pytest.fixture
def valid_request():
    token_value = ('testtest' + consts.SALT).encode('utf-8')
    token = hashlib.sha512(token_value).hexdigest()

    return {
        'account': 'test',
        'login': 'test',
        'method': 'clients_interests',
        'arguments': {
            'client_ids': [1, 2],
            'date': '01.01.2000',
        },
        'token': token,
    }


class TestGetInterests:
    @staticmethod
    def _send_request(request, store):
        return method_handler(
            request={
                'body': request,
                'headers': {},
            },
            ctx={},
            store=store,
        )

    def test_get_interests(self, store: RedisStore, valid_request):
        store.set('i:1', json.dumps(['one', 'two']))
        store.set('i:2', json.dumps(['three']))

        response, code = self._send_request(valid_request, store)
        assert code == consts.OK

        assert response.get('1') == ['one', 'two']
        assert response.get('2') == ['three']

    def test_get_interests_unavailable_store(
        self,
        unavailable_store,
        valid_request,
    ):
        with pytest.raises(ConnectionError):
            self._send_request(valid_request, unavailable_store)
