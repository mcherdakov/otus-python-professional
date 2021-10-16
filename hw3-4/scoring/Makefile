default: run

up:
	sudo docker-compose up -d

down:
	sudo docker-compose down

build: 
	sudo docker-compose build

sh:
	sudo docker-compose exec scoring-api sh

run: build up

debug: build
	sudo docker-compose up


build-test:
	sudo docker-compose -f docker-compose.test.yaml build -q

test_integration: build-test
	sudo docker-compose -f docker-compose.test.yaml up --abort-on-container-exit --remove-orphans

test_unit:
	pytest tests/unit --disable-pytest-warnings

test: test_unit test_integration
