# Scoring API

### How to run:

1. Install docker and docker-compose: [documentation](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)

2. `make run` (or simply `make`) to run it

3. get token:
```python
import consts
import hashlib
token_value = ('testtest' + consts.SALT).encode('utf-8')
token = hashlib.sha512(token_value).hexdigest()
```

4. send request:
```bash
curl --location --request POST 'http://127.0.0.1:8080/method/' --header 'Content-Type: application/json' --data-raw '{
    "account": "test",
    "login": "test",
    "method": "clients_interests",
    "token": "<token>",
 "arguments": {
        "client_ids": [
            1,
            2,
            3,
            4
        ],
        "date": "20.07.2017"
    }
}'
```

### How to test:

`make test` to run all tests or `make test_unit && make test_integration`
