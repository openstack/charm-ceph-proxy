#!/usr/bin/make
PYTHON := /usr/bin/env python

lint:
	@flake8 --exclude hooks/charmhelpers hooks
	@charm proof

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
