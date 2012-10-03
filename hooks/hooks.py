#!/usr/bin/python

#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  Paul Collins <paul.collins@canonical.com>
#

import glob
import os
import subprocess
import shutil
import socket
import sys

import ceph
import utils

def install_upstart_scripts():
    for x in glob.glob('files/upstart/*.conf'):
        shutil.copy(x, '/etc/init/') 

def install():
    utils.juju_log('INFO', 'Begin install hook.')
    utils.configure_source()
    utils.install('ceph')
    utils.install('gdisk') # for ceph-disk-prepare

    install_upstart_scripts()

    utils.juju_log('INFO', 'End install hook.')

def emit_cephconf():
    cephcontext = {
        'mon_hosts': ' '.join(get_mon_hosts()),
        'fsid': utils.config_get('fsid'),
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

    emit_cephconf()

    if ceph.is_quorum():
        for dev in utils.config_get('osd-devices').split(' '):
            osdize_and_activate(dev)

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

    hosts.sort()
    return hosts

def bootstrap_monitor_cluster():
    hostname = utils.get_unit_hostname()
    done = "/var/lib/ceph/mon/ceph-%s/done" % hostname
    secret = utils.config_get('monitor-secret')
    keyring = "/var/lib/ceph/tmp/%s.mon.keyring" % hostname

    if os.path.exists(done):
        utils.juju_log('INFO', 'bootstrap_monitor_cluster: mon already initialized, getting on with life.')
    else:
        try:
            subprocess.check_call(['ceph-authtool', keyring,
                                   '--create-keyring', '--name=mon.',
                                   "--add-key=%s" % secret,
                                   '--cap', 'mon', 'allow *'])

            subprocess.check_call(['ceph-mon', '--mkfs',
                                   '-i', hostname,
                                   '--keyring', keyring])

            with open(done, 'w'):
                pass

            subprocess.check_call(['start', 'ceph-mon-all-starter'])
        except:
            raise
        finally:
            os.unlink(keyring)

def osdize_and_activate(dev):
    # XXX hack for instances
    subprocess.call(['umount', '/mnt'])

    if subprocess.call(['grep', '-wqs', dev + '1', '/proc/mounts']) == 0:
        utils.juju_log('INFO', "Looks like %s is in use, skipping." % dev)
        return True

    if os.path.exists(dev):
        subprocess.call(['ceph-disk-prepare', dev])
        subprocess.call(['udevadm', 'trigger',
                         '--subsystem-match=block', '--action=add'])

def mon_relation():
    utils.juju_log('INFO', 'Begin mon-relation hook.')
    emit_cephconf()

    moncount = int(utils.config_get('monitor-count'))
    if len(get_mon_hosts()) == moncount:
        bootstrap_monitor_cluster()

        ceph.wait_for_quorum()
        for dev in utils.config_get('osd-devices').split(' '):
            osdize_and_activate(dev)
    else:
        utils.juju_log('INFO',
                       "Not enough mons (%d), punting." % len(get_mon_hosts()))

    utils.juju_log('INFO', 'End mon-relation hook.')

def upgrade_charm():
    utils.juju_log('INFO', 'Begin upgrade-charm hook.')
    emit_cephconf()
    install_upstart_scripts()
    utils.install('gdisk') # for ceph-disk-prepare
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
