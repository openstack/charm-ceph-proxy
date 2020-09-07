#!/usr/bin/env python3
import os
from subprocess import CalledProcessError
import sys

_path = os.path.dirname(os.path.realpath(__file__))
_hooks = os.path.abspath(os.path.join(_path, '../hooks'))
_root = os.path.abspath(os.path.join(_path, '..'))


def _add_path(path):
    if path not in sys.path:
        sys.path.insert(1, path)

_add_path(_hooks)
_add_path(_root)

from charmhelpers.contrib.storage.linux.ceph import Pool, pool_exists
from charmhelpers.core.hookenv import action_get, config, log, action_fail

__author__ = 'chris'


def delete_cache_tier():
    backer_pool = action_get("backer-pool")
    cache_pool = action_get("cache-pool")
    user = config('admin-user')
    # Pre flight checks
    if not pool_exists(user, backer_pool):
        log("Backer pool {} must exist before calling this".format(
            backer_pool))
        action_fail("remove-cache-tier failed. Backer pool {} must exist "
                    "before calling this".format(backer_pool))

    if not pool_exists(user, cache_pool):
        log("Cache pool {} must exist before calling this".format(
            cache_pool))
        action_fail("remove-cache-tier failed. Cache pool {} must exist "
                    "before calling this".format(cache_pool))

    pool = Pool(service=user, name=backer_pool)
    try:
        pool.remove_cache_tier(cache_pool=cache_pool)
    except CalledProcessError as err:
        log("Removing the cache tier failed with message: {}".format(
            str(err)))
        action_fail("remove-cache-tier failed. Removing the cache tier failed "
                    "with message: {}".format(str(err)))


if __name__ == '__main__':
    delete_cache_tier()
