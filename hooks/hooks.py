#!/usr/bin/python

#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  Paul Collins <paul.collins@canonical.com>
#

import os
import subprocess
import socket
import sys

import ceph
import utils

def install():
    utils.juju_log('INFO', 'Begin install hook.')
    utils.configure_source()
    utils.install('ceph')

    # TODO: Install the upstart scripts.
    utils.juju_log('INFO', 'End install hook.')

def emit_cephconf():
    cephcontext = {
        'mon_hosts': ' '.join(get_mon_hosts())
        }

    with open('/etc/ceph/ceph.conf', 'w') as cephconf:
        cephconf.write(utils.render_template('ceph.conf', cephcontext))

def config_changed():
    utils.juju_log('INFO', 'Begin config-changed hook.')

    utils.juju_log('INFO', 'Monitor hosts are ' + repr(get_mon_hosts()))

    fsid = utils.config_get('fsid')
    if fsid == "":
        utils.juju_log('CRITICAL', 'No fsid supplied, cannot proceed.')
        sys.exit(1)

    monitor_secret = utils.config_get('monitor-secret')
    if monitor_secret == "":
        utils.juju_log('CRITICAL', 'No monitor-secret supplied, cannot proceed.')
        sys.exit(1)

    osd_devices = utils.config_get('osd-devices')

    emit_cephconf()

    utils.juju_log('INFO', 'End config-changed hook.')

def get_mon_hosts():
    hosts = []
    hosts.append(socket.gethostbyname(utils.unit_get('private-address'))
                 + ':6789')

    for relid in utils.relation_ids("mon"):
        for unit in utils.relation_list(relid):
            hosts.append(
                socket.gethostbyname(utils.relation_get('private-address',
                                                        unit, relid))
                + ':6789')

    return hosts

def mon_relation():
    utils.juju_log('INFO', 'Begin mon-relation hook.')
    emit_cephconf()
    utils.juju_log('INFO', 'End mon-relation hook.')

def upgrade_charm():
    utils.juju_log('INFO', 'Begin upgrade-charm hook.')
    emit_cephconf()
    utils.juju_log('INFO', 'End upgrade-charm hook.')

hooks = {
    'config-changed': config_changed,
    'install': install,
    'mon-relation-changed': mon_relation,
    'mon-relation-departed': mon_relation,
    'mon-relation-joined': mon_relation,
    'upgrade-charm': upgrade_charm,
}

hook = os.path.basename(sys.argv[0])

try:
    hooks[hook]()
except KeyError:
    utils.juju_log('INFO', "This charm doesn't know how to handle '%s'." % hook)

sys.exit(0)
