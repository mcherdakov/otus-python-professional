from datetime import datetime

import pytest
from app.consts import ADMIN_LOGIN
from app.fields import ValidationError
from app.methods import MethodRequest, OnlineScoreRequest, online_score_handler
from app.scoring import get_score

from .conftest import FakeStore


class TestScoring:
    @pytest.mark.parametrize(
        'phone,email,birthday,gender,first_name,last_name,expected',
        (
            ('+79991234567', None, None, None, None, None, 1.5),
            ('+79991234567', 'a@b', None, None, None, None, 3.),
            ('+79991234567', 'a@b', datetime.now(), None, None, None, 3.),
            ('+79991234567', 'a@b', datetime.now(), 1, None, None, 4.5),
            ('+79991234567', 'a@b', datetime.now(), 1, 'a', 'b', 5.),
        )
    )
    def test_get_score(
        self, fake_store: FakeStore,
        phone, email, birthday, gender,
        first_name, last_name, expected,
    ):
        assert abs(
            get_score(
                fake_store, phone, email, birthday,
                gender, first_name, last_name,
            )
        ) - expected < 0.001

    def test_score_handler(self, fake_store: FakeStore):
        request = MethodRequest(
            {
                'arguments': {
                    'phone': '79991234567',
                    'email': 'a@b.c',
                },
            }
        )

        ctx: dict = {}
        response = online_score_handler(request, ctx, fake_store)
        assert set(ctx['has']) == {'phone', 'email'}
        assert abs(response['score'] - 3.0) < 0.001

    def test_score_handler_admin(self, fake_store: FakeStore):
        request = MethodRequest(
            {
                'arguments': {
                    'phone': '79991234567',
                    'email': 'a@b.c',
                },
                'login': ADMIN_LOGIN,
            }
        )

        response = online_score_handler(request, {}, fake_store)
        assert abs(response['score'] - 42.) < 0.001

    @pytest.mark.parametrize(
        'args',
        (
            {
                'phone': '79991234567',
                'email': 'a@b.c',
            },
            {
                'first_name': 'Harry',
                'last_name': 'Potter',
            },
            {
                'birthday': '12.12.2021',
                'gender': 1,
            }
        )
    )
    def test_request_validation_valid(self, args):
        req = OnlineScoreRequest(args)
        req.validate()

    @pytest.mark.parametrize(
        'args',
        (
            {
                'phone': '79991234567',
                'first_name': 'Harry',
            },
            {
                'last_name': 'Potter',
            },
            {
                'birthday': '12.12.2021',
            },
            {},
            {
                'phone': '7999123',
                'email': 'a@b.c',
            },
            {
                'phone': '79991234567',
                'email': 'invalid',
            },
            {
                'birthday': '12.12.12',
                'gender': 1,
            }
        )
    )
    def test_request_validation_invalid(self, args):
        req = OnlineScoreRequest(args)
        with pytest.raises(ValidationError):
            req.validate()
