import functools
import logging
import time

from redis import Redis
from redis.exceptions import ConnectionError, TimeoutError


def safe_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (TimeoutError, ConnectionError) as e:
            logging.error(e)
            return None

    return wrapper


class RedisStore:
    def __init__(
        self,
        host: str,
        port: int,
        timeout: int = 10,
        retry_count: int = 3,
        retry_initial_interval: int = 1,
        backoff: int = 2,
    ) -> None:
        self.client = Redis(
            host=host,
            port=port,
            db=0,
            socket_timeout=timeout,
        )
        self.retry_count = retry_count
        self.retry_initial_interval = retry_initial_interval
        self.backoff = backoff

    @safe_call
    def cache_get(self, key: str) -> str | None:
        return self.get(key, retry=False)

    @safe_call
    def cache_set(self, key: str, value, ttl: int):
        """
        ttl: in seconds
        """
        return self.client.set(key, value, ex=ttl)

    def _retry(self, f, *args, **kwargs):
        exception = None
        for i in range(self.retry_count):
            try:
                return f(*args, **kwargs)
            except (TimeoutError, ConnectionError) as e:
                logging.error(e)
                time.sleep(self.retry_initial_interval * self.backoff ** i)
                exception = e

        raise exception

    def get(self, key, retry=True) -> str | None:
        if retry:
            value = self._retry(self.client.get, key)
        else:
            value = self.client.get(key)

        if value is None:
            return None

        return value.decode('utf-8')

    def set(self, key, value) -> bool | None:
        return self._retry(self.client.set, key, value)
