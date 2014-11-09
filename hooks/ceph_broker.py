#!/usr/bin/python
#
# Copyright 2014 Canonical Ltd.
#
import json

from charmhelpers.core.hookenv import (
    log,
    INFO,
    ERROR
)
from charmhelpers.contrib.storage.linux.ceph import (
    create_pool,
    pool_exists
)


def decode(f):
    def decode_inner(req):
        return json.dumps(f(json.loads(req)))

    return decode_inner


@decode
def process_requests(reqs):
    """Process a Ceph broker request from a ceph client.

    This is a versioned api. We choose the api version based on provided
    version from client.
    """
    version = reqs.get('api-version')
    if version == 1:
        return process_requests_v1(reqs['ops'])

    msg = ("Missing or invalid api version (%s)" % (version))
    return {'exit-code': 1, 'stderr': msg}


def process_requests_v1(reqs):
    """Process a v1 requests from a ceph client.

    Takes a list of requests (dicts) and processes each one until it hits an
    error.

    Upon completion of all ops or if an error is found, a response dict is
    returned containing exit code and any extra info.
    """
    log("Processing %s ceph broker requests" % (len(reqs)), level=INFO)
    for req in reqs:
        op = req.get('op')
        log("Processing op='%s'" % (op), level=INFO)
        # Use admin client since we do not have other client key locations
        # setup to use them for these operations.
        svc = 'admin'
        if op == "create-pool":
            params = {'pool': req.get('name'),
                      'replicas': req.get('replicas')}
            if not all(params.iteritems()):
                msg = ("Missing parameter(s): %s" %
                       (' '.join([k for k in params.iterkeys()
                                  if not params[k]])))
                log(msg, level=ERROR)
                return {'exit-code': 1, 'stderr': msg}

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
            msg = "Unknown operation '%s'" % (op)
            log(msg, level=ERROR)
            return {'exit-code': 1, 'stderr': msg}

    return {'exit-code': 0}
