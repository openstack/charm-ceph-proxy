#!/usr/bin/python

#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  Paul Collins <paul.collins@canonical.com>
#  James Page <james.page@ubuntu.com>
#

import glob
import os
import random
import shutil
import socket
import subprocess
import sys
import uuid
import time

import ceph
from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    config,
    relation_ids,
    related_units,
    relation_get,
    relation_set,
    leader_set, leader_get,
    is_leader,
    remote_unit,
    Hooks, UnregisteredHookError,
    service_name,
    relations_of_type,
    status_set,
    local_unit)
from charmhelpers.core.host import (
    service_restart,
    mkdir,
    write_file,
    rsync,
    cmp_pkgrevno,
    service_stop, service_start)
from charmhelpers.fetch import (
    apt_install,
    apt_update,
    filter_installed_packages,
    add_source
)
from charmhelpers.payload.execd import execd_preinstall
from charmhelpers.contrib.openstack.alternatives import install_alternative
from charmhelpers.contrib.network.ip import (
    get_ipv6_addr,
    format_ipv6_addr,
)
from charmhelpers.core.sysctl import create as create_sysctl
from charmhelpers.core.templating import render
from charmhelpers.contrib.storage.linux.ceph import (
    monitor_key_set,
    monitor_key_exists,
    monitor_key_get,
    get_mon_map)

from ceph_broker import (
    process_requests
)

from utils import (
    get_public_addr,
    get_unit_hostname,
)

from charmhelpers.contrib.charmsupport import nrpe
from charmhelpers.contrib.hardening.harden import harden

hooks = Hooks()


def install_upstart_scripts():
    # Only install upstart configurations for older versions
    if cmp_pkgrevno('ceph', "0.55.1") < 0:
        for x in glob.glob('files/upstart/*.conf'):
            shutil.copy(x, '/etc/init/')


@hooks.hook('install.real')
@harden()
def install():
    execd_preinstall()
    add_source(config('source'), config('key'))
    apt_update(fatal=True)
    apt_install(packages=ceph.PACKAGES, fatal=True)
    install_upstart_scripts()


def emit_cephconf():

    cephcontext = {
        'mon_hosts': config('monitor-hosts'),
        'fsid': config('fsid'),
        'use_syslog': str(config('use-syslog')).lower(),
        'loglevel': config('loglevel'),
    }

    # Install ceph.conf as an alternative to support
    # co-existence with other charms that write this file
    charm_ceph_conf = "/var/lib/charm/{}/ceph.conf".format(service_name())
    mkdir(os.path.dirname(charm_ceph_conf), owner=ceph.ceph_user(),
          group=ceph.ceph_user())
    render('ceph.conf', charm_ceph_conf, cephcontext, perms=0o644)
    install_alternative('ceph.conf', '/etc/ceph/ceph.conf',
                        charm_ceph_conf, 100)
    keyring = 'ceph.client.admin.keyring'
    keyring_path = '/etc/ceph/' + keyring
    render(keyring, keyring_path, {'admin_key': config('admin-key')}, perms=0o600)

    keyring = 'keyring'
    keyring_path = '/var/lib/ceph/mon/ceph-' + get_unit_hostname()+ '/' + keyring
    render('mon.keyring', keyring_path, {'mon_key': config('mon-key')}, perms=0o600)

    notify_radosgws()
    notify_client()

@hooks.hook('config-changed')
@harden()
def config_changed():
    emit_cephconf()


def notify_radosgws():
    for relid in relation_ids('radosgw'):
        for unit in related_units(relid):
            radosgw_relation(relid=relid, unit=unit)


def notify_client():
    for relid in relation_ids('client'):
        client_relation_joined(relid)


@hooks.hook('radosgw-relation-changed')
@hooks.hook('radosgw-relation-joined')
def radosgw_relation(relid=None, unit=None):
    # Install radosgw for admin tools
    apt_install(packages=filter_installed_packages(['radosgw']))
    if not unit:
        unit = remote_unit()

    # NOTE: radosgw needs some usage OSD storage, so defer key
    #       provision until OSD units are detected.
    if ready():
        log('mon cluster in quorum and osds related '
            '- providing radosgw with keys')
        public_addr = get_public_addr()
        data = {
            'fsid': config('fsid'),
            'radosgw_key': ceph.get_radosgw_key(),
            'auth': 'cephx',
            'ceph-public-address': public_addr,
        }

        settings = relation_get(rid=relid, unit=unit)
        """Process broker request(s)."""
        if 'broker_req' in settings:
            if ceph.is_leader():
                rsp = process_requests(settings['broker_req'])
                unit_id = unit.replace('/', '-')
                unit_response_key = 'broker-rsp-' + unit_id
                data[unit_response_key] = rsp
            else:
                log("Not leader - ignoring broker request", level=DEBUG)

        relation_set(relation_id=relid, relation_settings=data)
    else:
        log('FSID or admin key not provided, please configure them')


@hooks.hook('client-relation-joined')
def client_relation_joined(relid=None):
    if ready():
        service_name = None
        if relid is None:
            units = [remote_unit()]
            service_name = units[0].split('/')[0]
        else:
            units = related_units(relid)
            if len(units) > 0:
                service_name = units[0].split('/')[0]

        if service_name is not None:
            public_addr = get_public_addr()
            data = {'key': ceph.get_named_key(service_name),
                    'auth': 'cephx',
                    'ceph-public-address': public_addr}
            relation_set(relation_id=relid,
                         relation_settings=data)
    else:
        log('FSID or admin key not provided, please configure them')


@hooks.hook('client-relation-changed')
def client_relation_changed():
    """Process broker requests from ceph client relations."""
    if ready():
        settings = relation_get()
        if 'broker_req' in settings:
            if not ceph.is_leader():
                log("Not leader - ignoring broker request", level=DEBUG)
            else:
                rsp = process_requests(settings['broker_req'])
                unit_id = remote_unit().replace('/', '-')
                unit_response_key = 'broker-rsp-' + unit_id
                # broker_rsp is being left for backward compatibility,
                # unit_response_key superscedes it
                data = {
                    'broker_rsp': rsp,
                    unit_response_key: rsp,
                }
                relation_set(relation_settings=data)
    else:
        log('FSID or admin key not provided, please configure them')


def ready():
    return config('fsid') and config('admin-key')


def assess_status():
    '''Assess status of current unit'''
    if ready():
        status_set('active', 'Ready to proxy settings')
    else:
        status_set('blocked', 'Ensure FSID and admin-key are set')
    # moncount = int(config('monitor-count'))
    # units = get_peer_units()
    # # not enough peers and mon_count > 1
    # if len(units.keys()) < moncount:
    #     status_set('blocked', 'Insufficient peer units to bootstrap'
    #                           ' cluster (require {})'.format(moncount))
    #     return

    # # mon_count > 1, peers, but no ceph-public-address
    # ready = sum(1 for unit_ready in units.itervalues() if unit_ready)
    # if ready < moncount:
    #     status_set('waiting', 'Peer units detected, waiting for addresses')
    #     return

    # # active - bootstrapped + quorum status check
    # if ceph.is_bootstrapped() and ceph.is_quorum():
    #     status_set('active', 'Unit is ready and clustered')
    # else:
    #     # Unit should be running and clustered, but no quorum
    #     # TODO: should this be blocked or waiting?
    #     status_set('blocked', 'Unit not clustered (no quorum)')
    #     # If there's a pending lock for this unit,
    #     # can i get the lock?
    #     # reboot the ceph-mon process
    # status_set('active', 'doing some shit maybe?')


@hooks.hook('update-status')
@harden()
def update_status():
    log('Updating status.')


if __name__ == '__main__':
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))
    assess_status()
