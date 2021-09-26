from datetime import datetime
from weakref import WeakKeyDictionary

UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: 'unknown',
    MALE: 'male',
    FEMALE: 'female',
}


class Field:
    valid_types: list[type] = []

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable
        self.data = WeakKeyDictionary()

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        return self.data[instance]

    def __set__(self, instance, value):
        self.validate(value)
        self.data[instance] = value

    def validate(self, value):
        if value is None and not self.nullable:
            raise AttributeError(
                f'{self.name}: non-nullable filed value is None',
            )

        if value is None and self.nullable:
            return

        for valid_type in self.valid_types:
            if isinstance(value, valid_type):
                return

        types = [t.__name__ for t in self.valid_types]
        raise AttributeError(
                f'{self.name}: type must be one of {types}',
            )


class CharField(Field):
    valid_types = [str]


class ArgumentsField(Field):
    valid_types = [dict]


class EmailField(CharField):
    valid_types = [str]

    def validate(self, value):
        super().validate(value)

        if value is None:
            return

        if '@' not in value:
            raise AttributeError(
                f'{self.name}: invalid email address',
            )


class PhoneField(Field):
    valid_types = [str, int]

    def validate(self, value):
        super().validate(value)

        if value is None:
            return

        s_value = str(value)
        if len(s_value) != 11 or s_value[0] != '7':
            raise AttributeError(
                f'{self.name}: phone number must be'
                f' 11 digits long and start with "7"',
            )


class DateField(CharField):
    FORMAT = "%d.%m.%Y"

    def validate(self, value):
        super().validate(value)

        if value is None:
            return

        try:
            datetime.strptime(value, self.FORMAT)
        except ValueError as e:
            raise AttributeError(f'{self.name}: {str(e)}')


class BirthDayField(DateField):
    def validate(self, value):
        super().validate(value)

        if value is None:
            return

        td = datetime.now() - datetime.strptime(value, self.FORMAT)
        # approximately 70 years
        if td.days > 70 * 365:
            raise AttributeError(
                f'{self.name}: age must be < 70',
            )


class GenderField(Field):
    valid_types = [int]

    def validate(self, value):
        super().validate(value)

        if value is None:
            return

        possible_values = [0, 1, 2]
        if value not in possible_values:
            raise AttributeError(
                f'{self.name}: must be in {possible_values}',
            )


class ClientIDsField(Field):
    valid_types = [list]

    def validate(self, value):
        super().validate(value)

        if len(value) == 0:
            raise AttributeError(
                f'{self.name}: must not be empty',
            )

        if not all(isinstance(v, int) for v in value):
            raise AttributeError(
                f'{self.name}: all members must be integers',
            )