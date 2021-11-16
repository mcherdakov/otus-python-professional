import hashlib

import pytest
from app import consts
from app.api import method_handler
from app.store import RedisStore


@pytest.fixture
def valid_request():
    token_value = ('testtest' + consts.SALT).encode('utf-8')
    token = hashlib.sha512(token_value).hexdigest()

    return {
        'account': 'test',
        'login': 'test',
        'method': 'online_score',
        'arguments': {
            'gender': 1,
            'birthday': '01.01.2000',
        },
        'token': token,
    }


class TestGetScore:
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

    def test_get_score_no_cache(self, store: RedisStore, valid_request):
        response, code = self._send_request(valid_request, store)
        assert code == consts.OK
        assert abs(response.get('score') - 1.5) < .001

    def test_get_score_cache(self, store: RedisStore, valid_request):
        key = "uid:" + hashlib.md5('20000101'.encode('utf-8')).hexdigest()
        store.cache_set(key, 10., ttl=1000)

        response, code = self._send_request(valid_request, store)
        assert code == consts.OK
        assert abs(response.get('score') - 10.) < .001

    def test_get_score_unavailable_cache(
        self,
        unavailable_store,
        valid_request,
    ):
        response, code = self._send_request(valid_request, unavailable_store)
        assert code == consts.OK
        assert abs(response.get('score') - 1.5) < .001
