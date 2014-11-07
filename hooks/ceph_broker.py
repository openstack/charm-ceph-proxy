#!/usr/bin/python
#
# Copyright 2014 Canonical Ltd.
#
from charmhelpers.core.hookenv import (
    log,
    INFO,
    ERROR
)
from charmhelpers.contrib.storage.linux.ceph import (
    create_pool,
    pool_exists,
    ensure_ceph_keyring
)


def process_requests(reqs):
    """Process a Ceph broker request from a ceph client."""
    log("Processing %s ceph broker requests" % (len(reqs)), level=INFO)
    for req in reqs:
        op = req.get('op')
        log("Processing op='%s'" % (op), level=INFO)
        # Use admin client since we do not have other client key locations
        # setup to use them for these operations.
        svc = 'admin'
        if op == "create_pool":
            pool = req.get('pool')
            replicas = req.get('replicas')
            if not all([pool, replicas]):
                log("Missing parameter(s)", level=ERROR)
                return 1

            if not pool_exists(service=svc, name=pool):
                log("Creating pool '%s'" % (pool), level=INFO)
                create_pool(service=svc, name=pool, replicas=replicas)
            else:
                log("Pool '%s' already exists" % (pool), level=INFO)
        elif op == "create_keyring":
            user = req.get('user')
            group = req.get('group')
            if not all([user, group]):
                log("Missing parameter(s)", level=ERROR)
                return 1

            ensure_ceph_keyring(service=svc, user=user, group=group)

    return 0
