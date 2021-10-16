import pytest
from app.store import RedisStore
from redis.exceptions import ConnectionError


class TestRedisStore:
    def test_persistent(self, store: RedisStore):
        store.set('hello', 'world')
        value = store.get('hello')

        assert value == 'world'

    def test_cache(self, store: RedisStore):
        store.cache_set('hello', 'world', ttl=1000)
        value = store.cache_get('hello')

        assert value == 'world'

    def test_persistent_does_not_exist(self, store: RedisStore):
        assert store.get('hello') is None

    def test_cache_does_not_exist(self, store: RedisStore):
        assert store.cache_get('hello') is None

    def test_unavailable_persistent(
        self,
        unavailable_store: RedisStore,
    ):
        with pytest.raises(ConnectionError):
            unavailable_store.set('hello', 'world')

        with pytest.raises(ConnectionError):
            unavailable_store.get('hello')

    def test_unavailable_cache(
        self,
        unavailable_store: RedisStore,
    ):
        unavailable_store.cache_set('hello', 'world', ttl=1000)
        assert unavailable_store.cache_get('hello') is None
