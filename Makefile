.PHONY: help
VERSION:=$(shell grep VERSION setup.py | head -n1 | cut -d"'" -f2)

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
	docker run --name test-prometheus-data-generator --tty -v `pwd`:/tox --rm \
		alexperezpujol/tox:latest tox

docker-build:
	docker build -t mksmki/prometheus-data-generator .

docker-push:
	@docker tag mksmki/prometheus-data-generator:latest mksmki/prometheus-data-generator:$(VERSION)
	@docker push mksmki/prometheus-data-generator:latest
	@docker push mksmki/prometheus-data-generator:$(VERSION)

all: clean test build
