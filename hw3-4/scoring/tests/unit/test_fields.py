from datetime import datetime

import pytest
from app import fields


def _wrap_descriptor(field_name, descriptor_class, descriptor_args):
    return type(
        "FieldTest",
        (object,),
        {
            field_name: descriptor_class(**descriptor_args),
        }
    )()


class TestField:
    def test_set_value(self):
        class Desc(fields.Field):
            valid_types = [str]

        desc_class = _wrap_descriptor(
            field_name='f',
            descriptor_class=Desc,
            descriptor_args={},
        )
        desc_class.f = 'hello'

        assert desc_class.f == 'hello'

    def test_validate_null_nullable(self):
        desc = fields.Field(nullable=True)
        desc.name = 'some_field'
        desc.validate(None)

    def test_validate_null_non_nullable(self):
        desc = fields.Field(nullable=False)
        desc.name = 'some_field'

        with pytest.raises(fields.ValidationError):
            desc.validate(None)

    def test_validate_type(self):
        desc = fields.Field()
        desc.valid_types = [str]
        desc.name = 'some_field'

        with pytest.raises(fields.ValidationError):
            desc.validate(123)


VALIDATION_TEST_CASES: list[dict] = [
    {
        'descriptor': fields.CharField,
        'valid_cases': [
            {'value': 'hello', 'result': 'hello'},
            {'value': '', 'result': ''},
        ],
        'invalid_cases': [123, .42, Exception],
    },
    {
        'descriptor': fields.ArgumentsField,
        'valid_cases': [
            {'value': {}, 'result': {}},
            {'value': {'hello': 'world'}, 'result': {'hello': 'world'}},
        ],
        'invalid_cases': [123, 'hello'],
    },
    {
        'descriptor': fields.EmailField,
        'valid_cases': [
            {'value': '@', 'result': '@'},
            {'value': 'a@b', 'result': 'a@b'},
        ],
        'invalid_cases': [123, 'hello', ''],
    },
    {
        'descriptor': fields.PhoneField,
        'valid_cases': [
            {'value': '71234567890', 'result': '71234567890'},
            {'value': 71234567890, 'result': 71234567890},
        ],
        'invalid_cases': ['', 123, '456', '7123456789', '12345678901'],
    },
    {
        'descriptor': fields.DateField,
        'valid_cases': [
            {
                'value': '11.12.1999',
                'result': datetime(day=11, month=12, year=1999),
            },
        ],
        'invalid_cases': [123, '13.13.1999', '12.12.12'],
    },
    {
        'descriptor': fields.BirthDayField,
        'valid_cases': [
            {
                'value': '11.12.2021',
                'result': datetime(day=11, month=12, year=2021),
            },
        ],
        'invalid_cases': ['11.12.1884'],
    },
    {
        'descriptor': fields.GenderField,
        'valid_cases': [
            {'value': 0, 'result': 0},
            {'value': 1, 'result': 1},
            {'value': 2, 'result': 2},
        ],
        'invalid_cases': [-1, 3, '2'],
    },
    {
        'descriptor': fields.ClientIDsField,
        'valid_cases': [
            {'value': [1, 2], 'result': [1, 2]},
        ],
        'invalid_cases': [123, [], ['1', 2]],
    },
]


VALID_TEST_CASES = []
INVALID_TEST_CASES = []
for suite in VALIDATION_TEST_CASES:
    descr = suite['descriptor']
    for test_case in suite['valid_cases']:
        VALID_TEST_CASES.append((descr, test_case))
    for test_case in suite['invalid_cases']:
        INVALID_TEST_CASES.append((descr, test_case))


class TestFieldValidation:
    @pytest.mark.parametrize(
        'descriptor,case',
        VALID_TEST_CASES,
    )
    def test_valid(self, descriptor, case):
        desc_class = _wrap_descriptor(
            field_name='f',
            descriptor_class=descriptor,
            descriptor_args={},
        )
        desc_class.f = case['value']
        assert desc_class.f == case['result']

    @pytest.mark.parametrize(
        'descriptor,case',
        INVALID_TEST_CASES,
    )
    def test_invalid(self, descriptor, case):
        desc_class = _wrap_descriptor(
            field_name='f',
            descriptor_class=descriptor,
            descriptor_args={},
        )
        with pytest.raises(fields.ValidationError):
            desc_class.f = case
