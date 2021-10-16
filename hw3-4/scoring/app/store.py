import functools
import logging

from redis import Redis
from redis.exceptions import ConnectionError, TimeoutError


class Store:
    def cache_get(self, key):
        raise NotImplementedError

    def cache_set(self, key, value, ttl):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value):
        raise NotImplementedError


def safe_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (TimeoutError, ConnectionError) as e:
            logging.error(e)
            return None

    return wrapper


class RedisStore(Store):
    def __init__(self, host: str, port: int, timeout: int = 10) -> None:
        self.client = Redis(
            host=host,
            port=port,
            db=0,
            socket_timeout=timeout
        )

    @safe_call
    def cache_get(self, key: str) -> str | None:
        return self.get(key)

    @safe_call
    def cache_set(self, key: str, value, ttl: int):
        """
        ttl: in seconds
        """
        return self.client.set(key, value, ex=ttl)

    def get(self, key) -> str | None:
        value = self.client.get(key)
        if value is None:
            return None

        return value.decode('utf-8')

    def set(self, key, value) -> bool | None:
        return self.client.set(key, value)
