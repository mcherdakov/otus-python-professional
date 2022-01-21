default: dev

build-dev:
	sudo docker-compose -f docker-compose.dev.yaml build

build-test:
	sudo docker-compose -f docker-compose.test.yaml build

dev: build-dev
	sudo docker-compose -f docker-compose.dev.yaml up 

shell: build-dev
	sudo docker-compose -f docker-compose.dev.yaml run hasker python manage.py shell

migrate: build-dev
	sudo docker-compose -f docker-compose.dev.yaml run hasker python manage.py migrate

manage: build-dev
	sudo docker-compose -f docker-compose.dev.yaml run hasker python manage.py $(cmd)

test: build-dev
	sudo docker-compose -f docker-compose.dev.yaml run hasker python manage.py test

build-prod:
	sudo docker-compose -f docker-compose.prod.yaml build

prod: build-prod
	sudo docker-compose -f docker-compose.prod.yaml up

manage-prod: build-prod
	sudo docker-compose -f docker-compose.prod.yaml run hasker python manage.py $(cmd)
