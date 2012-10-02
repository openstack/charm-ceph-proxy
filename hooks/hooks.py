#!/usr/bin/python

#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  Paul Collins <paul.collins@canonical.com>
#

import os
import subprocess
import sys

import ceph
import utils

def install():
    utils.juju_log('INFO', 'Begin install hook.')
    utils.configure_source()
    utils.install('ceph')

    # TODO: Install the upstart scripts.
    utils.juju_log('INFO', 'End install hook.')

def config_changed():
    utils.juju_log('INFO', 'Begin config-changed hook.')
    fsid = utils.config_get('fsid')
    if fsid == "":
        utils.juju_log('CRITICAL', 'No fsid supplied, cannot proceed.')
        sys.exit(1)

    monitor_secret = utils.config_get('monitor-secret')
    if monitor_secret == "":
        utils.juju_log('CRITICAL', 'No monitor-secret supplied, cannot proceed.')
        sys.exit(1)

    osd_devices = utils.config_get('osd-devices')
    utils.juju_log('INFO', 'End config-changed hook.')

def mon_relation():
    print "mon_relation"

hooks = {
    'mon-relation-joined': mon_relation,
    'mon-relation-changed': mon_relation,
    'mon-relation-departed': mon_relation,
    'install': install,
    'config-changed': config_changed,
}

hook = os.path.basename(sys.argv[0])

try:
    hooks[hook]()
except KeyError:
    utils.juju_log('INFO', "This charm doesn't know how to handle '%s'." % hook)

sys.exit(0)
