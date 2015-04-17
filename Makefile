#!/usr/bin/make
PYTHON := /usr/bin/env python

lint:
	@flake8 --exclude hooks/charmhelpers hooks tests unit_tests
	@charm proof

unit_test:
	@echo Starting unit tests...
	@$(PYTHON) /usr/bin/nosetests --nologcapture --with-coverage  unit_tests

test:
	@echo Starting Amulet tests...
	# coreycb note: The -v should only be temporary until Amulet sends
	# raise_status() messages to stderr:
	#   https://bugs.launchpad.net/amulet/+bug/1320357
	@juju test -v -p AMULET_HTTP_PROXY,AMULET_OS_VIP --timeout 2700

bin/charm_helpers_sync.py:
	@mkdir -p bin
	@bzr cat lp:charm-helpers/tools/charm_helpers_sync/charm_helpers_sync.py \
        > bin/charm_helpers_sync.py

sync: bin/charm_helpers_sync.py
	$(PYTHON) bin/charm_helpers_sync.py -c charm-helpers-hooks.yaml
	$(PYTHON) bin/charm_helpers_sync.py -c charm-helpers-tests.yaml

publish: lint
	bzr push lp:charms/ceph
	bzr push lp:charms/trusty/ceph
