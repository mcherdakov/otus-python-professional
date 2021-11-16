from app import consts
from app.fields import (ArgumentsField, BirthDayField, CharField,
                        ClientIDsField, DateField, EmailField, Field,
                        GenderField, PhoneField, ValidationError)
from app.scoring import get_interests, get_score


class MethodNotFound(Exception):
    pass


class FieldSet:
    def __init__(self, data):
        self._fields = []
        for f_name, f_value in self.__class__.__dict__.items():
            if not isinstance(f_value, Field):
                continue

            self._fields.append(f_name)
            setattr(self, f'_{f_name}', data.get(f_name))

    def validate(self):
        for field in self._fields:
            field_value = getattr(self, f'_{field}')
            setattr(self, field, field_value)


class MethodRequest(FieldSet):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == consts.ADMIN_LOGIN


class ClientsInterestsRequest(FieldSet):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(FieldSet):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def validate(self):
        valid_sets = (
            ('phone', 'email'),
            ('first_name', 'last_name'),
            ('birthday', 'gender'),
        )

        one_valid_set_exists = any(
            all(getattr(self, field) is not None for field in valid_set)
            for valid_set in valid_sets
        )

        if not one_valid_set_exists:
            raise ValidationError('Not enough arguments')

        super().validate()


def online_score_handler(method_request, ctx: dict, store):
    args = method_request.arguments or {}
    request = OnlineScoreRequest(args)
    request.validate()

    ctx['has'] = list(args.keys())

    if method_request.is_admin:
        score = 42.
    else:
        score = get_score(
            store=store,
            phone=request.phone,
            email=request.email,
            birthday=request.birthday,
            gender=request.gender,
            first_name=request.first_name,
            last_name=request.last_name,
        )

    return {'score': score}


def clients_interests_handler(method_request, ctx, store):
    args = method_request.arguments or {}
    request = ClientsInterestsRequest(args)
    request.validate()

    ctx['nclients'] = len(request.client_ids)

    return {
        str(cid): get_interests(store, cid)
        for cid in request.client_ids
    }


AVAILABLE_METHODS = {
    'online_score': online_score_handler,
    'clients_interests': clients_interests_handler,
}


def process_method_request(method_request: MethodRequest, ctx, store):
    method = AVAILABLE_METHODS.get(method_request.method)
    if method is None:
        raise MethodNotFound()

    return method(method_request, ctx, store)
