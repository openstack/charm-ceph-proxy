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
    pool_exists
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
            params = {'pool': req.get('name'),
                      'replicas': req.get('replicas')}
            if not all(params.iteritems()):
                log("Missing parameter(s): %s" %
                    (' '.join([k for k in params.iterkeys()
                               if not params[k]])),
                    level=ERROR)
                return 1

            pool = params['pool']
            replicas = params['replicas']
            if not pool_exists(service=svc, name=pool):
                log("Creating pool '%s' (replicas=%s)" % (pool, replicas),
                    level=INFO)
                create_pool(service=svc, name=pool, replicas=replicas)
            else:
                log("Pool '%s' already exists - skipping create" % (pool),
                    level=INFO)
        else:
            log("Unknown operation '%s'" % (op))
            return 1

    return 0
