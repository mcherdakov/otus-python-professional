import json

import pytest


class FakeStore:
    def get(*args, **kwargs):
        return json.dumps(['hello', 'world'])

    def set(*args, **kwargs):
        pass

    def cache_get(*args, **kwargs):
        return None

    def cache_set(*args, **kwargs):
        pass


@pytest.fixture
def fake_store():
    return FakeStore()
