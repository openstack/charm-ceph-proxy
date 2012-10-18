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
import subprocess
import shutil
import sys

import ceph
import utils


def install_upstart_scripts():
    for x in glob.glob('files/upstart/*.conf'):
        shutil.copy(x, '/etc/init/')


def install():
    utils.juju_log('INFO', 'Begin install hook.')
    utils.configure_source()
    utils.install('ceph', 'gdisk', 'ntp')
    install_upstart_scripts()
    utils.juju_log('INFO', 'End install hook.')


def emit_cephconf():
    cephcontext = {
        'auth_supported': utils.config_get('auth-supported'),
        'mon_hosts': ' '.join(get_mon_hosts()),
        'fsid': utils.config_get('fsid'),
        }

    with open('/etc/ceph/ceph.conf', 'w') as cephconf:
        cephconf.write(utils.render_template('ceph.conf', cephcontext))


def config_changed():
    utils.juju_log('INFO', 'Begin config-changed hook.')

    utils.juju_log('INFO', 'Monitor hosts are ' + repr(get_mon_hosts()))

    fsid = utils.config_get('fsid')
    if fsid == '':
        utils.juju_log('CRITICAL', 'No fsid supplied, cannot proceed.')
        sys.exit(1)

    monitor_secret = utils.config_get('monitor-secret')
    if monitor_secret == '':
        utils.juju_log('CRITICAL',
                       'No monitor-secret supplied, cannot proceed.')
        sys.exit(1)

    emit_cephconf()

    for dev in utils.config_get('osd-devices').split(' '):
        osdize(dev)

    # Support use of single node ceph
    if (not ceph.is_bootstrapped() and
        int(utils.config_get('monitor-count')) == 1):
        bootstrap_monitor_cluster()
        ceph.wait_for_bootstrap()

    if ceph.is_bootstrapped():
        ceph.rescan_osd_devices()

    utils.juju_log('INFO', 'End config-changed hook.')


def get_mon_hosts():
    hosts = []
    hosts.append('{}:6789'.format(utils.get_host_ip()))

    for relid in utils.relation_ids('mon'):
        for unit in utils.relation_list(relid):
            hosts.append(
                '{}:6789'.format(utils.get_host_ip(
                                    utils.relation_get('private-address',
                                                       unit, relid)))
                )

    hosts.sort()
    return hosts


def bootstrap_monitor_cluster():
    hostname = utils.get_unit_hostname()
    done = '/var/lib/ceph/mon/ceph-{}/done'.format(hostname)
    secret = utils.config_get('monitor-secret')
    keyring = '/var/lib/ceph/tmp/{}.mon.keyring'.format(hostname)

    if os.path.exists(done):
        utils.juju_log('INFO',
                       'bootstrap_monitor_cluster: mon already initialized.')
    else:
        try:
            subprocess.check_call(['ceph-authtool', keyring,
                                   '--create-keyring', '--name=mon.',
                                   '--add-key={}'.format(secret),
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


def osdize(dev):
    e_mountpoint = utils.config_get('ephemeral-unmount')
    if e_mountpoint != "":
        subprocess.call(['umount', e_mountpoint])

    if ceph.is_osd_disk(dev):
        utils.juju_log('INFO',
                       'Looks like {} is already an OSD, skipping.'
                       .format(dev))
        return

    if subprocess.call(['grep', '-wqs', dev + '1', '/proc/mounts']) == 0:
        utils.juju_log('INFO',
                       'Looks like {} is in use, skipping.'.format(dev))
        return

    if os.path.exists(dev):
        subprocess.call(['ceph-disk-prepare', dev])


def mon_relation():
    utils.juju_log('INFO', 'Begin mon-relation hook.')
    emit_cephconf()

    moncount = int(utils.config_get('monitor-count'))
    if len(get_mon_hosts()) >= moncount:
        bootstrap_monitor_cluster()
        ceph.wait_for_bootstrap()
        ceph.rescan_osd_devices()
        notify_osds()
        notify_radosgws()
        notify_client()
    else:
        utils.juju_log('INFO',
                       'Not enough mons ({}), punting.'.format(
                            len(get_mon_hosts())))

    utils.juju_log('INFO', 'End mon-relation hook.')


def notify_osds():
    utils.juju_log('INFO', 'Begin notify_osds.')

    for relid in utils.relation_ids('osd'):
        utils.relation_set(fsid=utils.config_get('fsid'),
                           osd_bootstrap_key=ceph.get_osd_bootstrap_key(),
                           auth=utils.config_get('auth-supported'),
                           rid=relid)

    utils.juju_log('INFO', 'End notify_osds.')


def notify_radosgws():
    utils.juju_log('INFO', 'Begin notify_radosgws.')

    for relid in utils.relation_ids('radosgw'):
        utils.relation_set(radosgw_key=ceph.get_radosgw_key(),
                           auth=utils.config_get('auth-supported'),
                           rid=relid)

    utils.juju_log('INFO', 'End notify_radosgws.')


def notify_client():
    utils.juju_log('INFO', 'Begin notify_client.')

    for relid in utils.relation_ids('client'):
        service_name = utils.relation_list(relid)[0].split('/')[0]
        utils.relation_set(key=ceph.get_named_key(service_name),
                           auth=utils.config_get('auth-supported'),
                           rid=relid)

    utils.juju_log('INFO', 'End notify_client.')


def osd_relation():
    utils.juju_log('INFO', 'Begin osd-relation hook.')

    if ceph.is_quorum():
        utils.juju_log('INFO',
                       'mon cluster in quorum - providing fsid & keys')
        utils.relation_set(fsid=utils.config_get('fsid'),
                           osd_bootstrap_key=ceph.get_osd_bootstrap_key(),
                           auth=utils.config_get('auth-supported'))
    else:
        utils.juju_log('INFO',
                       'mon cluster not in quorum - deferring fsid provision')

    utils.juju_log('INFO', 'End osd-relation hook.')


def radosgw_relation():
    utils.juju_log('INFO', 'Begin radosgw-relation hook.')

    utils.install('radosgw')  # Install radosgw for admin tools

    if ceph.is_quorum():
        utils.juju_log('INFO',
                       'mon cluster in quorum - \
                        providing radosgw with keys')
        utils.relation_set(radosgw_key=ceph.get_radosgw_key(),
                           auth=utils.config_get('auth-supported'))
    else:
        utils.juju_log('INFO',
                       'mon cluster not in quorum - deferring key provision')

    utils.juju_log('INFO', 'End radosgw-relation hook.')


def client_relation():
    utils.juju_log('INFO', 'Begin client-relation hook.')

    if ceph.is_quorum():
        utils.juju_log('INFO',
                       'mon cluster in quorum - \
                        providing client with keys')
        service_name = os.environ['JUJU_REMOTE_UNIT'].split('/')[0]
        utils.relation_set(key=ceph.get_named_key(service_name),
                           auth=utils.config_get('auth-supported'))
    else:
        utils.juju_log('INFO',
                       'mon cluster not in quorum - deferring key provision')

    utils.juju_log('INFO', 'End client-relation hook.')


def upgrade_charm():
    utils.juju_log('INFO', 'Begin upgrade-charm hook.')
    emit_cephconf()
    install_upstart_scripts()
    utils.juju_log('INFO', 'End upgrade-charm hook.')


def start():
    # In case we're being redeployed to the same machines, try
    # to make sure everything is running as soon as possible.
    subprocess.call(['start', 'ceph-mon-all-starter'])
    ceph.rescan_osd_devices()


utils.do_hooks({
        'config-changed': config_changed,
        'install': install,
        'mon-relation-departed': mon_relation,
        'mon-relation-joined': mon_relation,
        'osd-relation-joined': osd_relation,
        'radosgw-relation-joined': radosgw_relation,
        'client-relation-joined': client_relation,
        'start': start,
        'upgrade-charm': upgrade_charm,
        })

sys.exit(0)
