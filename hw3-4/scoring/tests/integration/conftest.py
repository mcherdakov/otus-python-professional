import pytest
from app.store import RedisStore
from pytest_mock import MockerFixture
from redis.exceptions import ConnectionError


@pytest.fixture(scope='module')
def redis_db():
    # set up connection pool only onse
    store = RedisStore('redis', 6379)
    return store


@pytest.fixture(scope='function')
def store(redis_db: RedisStore):
    # function scope to clean up db
    yield redis_db
    redis_db.client.flushdb()


class UnavailableStore:
    def set(self, key, value, ex=None):
        raise ConnectionError

    def get(self, key):
        raise ConnectionError


@pytest.fixture
def unavailable_store(mocker: MockerFixture):
    store = RedisStore('redis', 6379, retry_initial_interval=0)
    mocker.patch.object(store, 'client', UnavailableStore())
    return store
