#!/usr/bin/make

lint:
	flake8 --exclude hooks/charmhelpers hooks
	charm proof
