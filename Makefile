#!/usr/bin/make

lint:
	@flake8 --exclude hooks/charmhelpers hooks
	@charm proof

sync:
	@charm-helper-sync -c charm-helpers-sync.yaml

publish: lint
	bzr push lp:charms/ceph
	bzr push lp:charms/trusty/ceph
