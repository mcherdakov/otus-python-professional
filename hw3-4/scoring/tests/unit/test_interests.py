import pytest
from app.fields import ValidationError
from app.methods import (ClientsInterestsRequest, MethodRequest,
                         clients_interests_handler)

from .conftest import FakeStore


class TestInterests:
    def test_interests_handler(self, fake_store: FakeStore):
        request = MethodRequest({
            'arguments': {
                'client_ids': [1, 2, 3],
                'date': '11.11.1999',
            }
        })

        ctx: dict = {}
        response = clients_interests_handler(request, ctx, fake_store)
        assert ctx['nclients'] == 3
        assert set(response.keys()) == {'1', '2', '3'}

    @pytest.mark.parametrize(
        'args',
        (
            {
                'client_ids': [1, 2, 3],
                'date': '11.11.1999',
            },
            {
                'client_ids': [1, 2, 3],
                'date': '11.11.1999',
            },
        )
    )
    def test_request_validation_valid(self, args):
        req = ClientsInterestsRequest(args)
        req.validate()

    @pytest.mark.parametrize(
        'args',
        (
            {},
            {
                'date': '11.11.1999',
            },
        )
    )
    def test_request_validation_invalid(self, args):
        req = ClientsInterestsRequest(args)
        with pytest.raises(ValidationError):
            req.validate()
