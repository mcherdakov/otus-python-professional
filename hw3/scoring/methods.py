import consts
from fields import (ArgumentsField, BirthDayField, CharField, ClientIDsField,
                    DateField, EmailField, Field, GenderField, PhoneField)
from scoring import get_interests, get_score


class MethodRequest(Field):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    def __init__(self, request: dict):
        body = request['body']
        self.account = body.get('account')
        self.login = body.get('login')
        self.token = body.get('token')
        self.arguments = body.get('arguments')
        self.method = body.get('method')

    @property
    def is_admin(self):
        return self.login == consts.ADMIN_LOGIN


class ClientsInterestsRequest(object):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def __init__(self, args: dict):
        self.client_ids = args.get('client_ids')
        self.date = args.get('date')


class OnlineScoreRequest(object):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, args: dict):
        self.first_name = args.get('first_name')
        self.last_name = args.get('last_name')
        self.email = args.get('email')
        self.phone = args.get('phone')
        self.birthday = args.get('birthday')
        self.gender = args.get('gender')


class TestRequest():
    c = CharField()

    def __init__(self, value):
        self.c = value


class Method:
    def __init__(self, method_request: MethodRequest):
        self.method_request = method_request

    def process(self, store, context):
        raise NotImplementedError


class OnlineScore(Method):
    def validate_arguments(self) -> bool:
        args = self.method_request.arguments
        if args is None:
            return False

        valid_sets = (
            ('phone', 'email'),
            ('first_name', 'last_name'),
            ('birthday', 'gender'),
        )

        return any(
            all(v in args for v in valid_set)
            for valid_set in valid_sets
        )

    def process(self, store, context) -> dict[str, float]:
        if not self.validate_arguments():
            raise AttributeError('Not enough arguments')

        args = self.method_request.arguments
        context['has'] = list(args.keys())

        request = OnlineScoreRequest(args)

        if self.method_request.is_admin:
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


class ClientsInterests(Method):
    def process(self, store, context) -> dict[str, float]:
        args = self.method_request.arguments

        request = ClientsInterestsRequest(args)
        context['nclients'] = len(request.client_ids)

        return {
            str(cid): get_interests(store, cid)
            for cid in request.client_ids
        }


AVAILABLE_METHODS = {
    'online_score': OnlineScore,
    'clients_interests': ClientsInterests,
}
