.PHONY: help
VERSION:=$(shell grep VERSION setup.py | head -n1 | cut -d"'" -f2)
TOX:=$(shell grep TOX setup.py | head -n1 | cut -d"'" -f2)

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "  clean                       remove *.pyc files, __pycache__ and *.egg-info directories"
	@echo "  test                        execute tests"
	@echo "  build                       build the docker image"
	@echo "  push                        push the docker image"
	@echo "Check the Makefile to know exactly what each target is doing."

clean:
	@echo "Deleting '*.pyc', '__pycache__' and '*.egg-info'..."
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr
	find . -name '*.egg-info' -type d | xargs rm -fr
	rm -fr dist build

test:
	docker run --rm --name test-prometheus-data-generator --tty -v `pwd`/app:/tox \
		-v `pwd`/tox.ini:/tox.ini:ro -w /tox \
		-v `pwd`/requirements.txt:/tox/requirements.txt:ro \
		kiwicom/tox:$(TOX)

docker-build:
	docker build \
		--builder default \
		-t mksmki/prometheus-data-generator .

docker-push:
	@docker tag mksmki/prometheus-data-generator:latest mksmki/prometheus-data-generator:$(VERSION)
	@docker push mksmki/prometheus-data-generator:latest
	@docker push mksmki/prometheus-data-generator:$(VERSION)

run:
	docker run --rm -ti -v `pwd`/config.yml:/home/appuser/config.yml -e PDG_LOG_LEVEL=DEBUG -p 127.0.0.1:9000:9000 \
		mksmki/prometheus-data-generator:latest

all: clean test build
