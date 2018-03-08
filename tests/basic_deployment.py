#!/usr/bin/env python

import amulet

from charmhelpers.contrib.openstack.amulet.deployment import (
    OpenStackAmuletDeployment
)
from charmhelpers.contrib.openstack.amulet.utils import (  # noqa
    OpenStackAmuletUtils,
    DEBUG,
    # ERROR
    )

# Use DEBUG to turn on debug logging
u = OpenStackAmuletUtils(DEBUG)


class CephBasicDeployment(OpenStackAmuletDeployment):
    """Amulet tests on a basic ceph deployment."""

    def __init__(self, series=None, openstack=None, source=None, stable=True):
        """Deploy the entire test environment."""
        super(CephBasicDeployment, self).__init__(series, openstack, source,
                                                  stable)
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()

        u.log.info('Waiting on extended status checks...')
        exclude_services = ['ceph-proxy', 'ceph-radosgw']

        # Wait for deployment ready msgs, except exclusions
        self._auto_wait_for_status(exclude_services=exclude_services)

        self._configure_proxy()
        self.d.sentry.wait()
        self._initialize_tests()
        self._auto_wait_for_status()

    def _add_services(self):
        """Add services

           Add the services that we're testing, where ceph is local,
           and the rest of the service are from lp branches that are
           compatible with the local charm (e.g. stable or next).
           """
        this_service = {'name': 'ceph-proxy'}
        other_services = [{'name': 'ceph-mon', 'units': 3},
                          {'name': 'ceph-osd', 'units': 3},
                          {'name': 'ceph-radosgw'}]
        super(CephBasicDeployment, self)._add_services(this_service,
                                                       other_services)

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'ceph-osd:mon': 'ceph-mon:osd',
            'ceph-radosgw:mon': 'ceph-proxy:radosgw',
        }
        super(CephBasicDeployment, self)._add_relations(relations)

    def _configure_services(self):
        ceph_config = {
            'monitor-count': '3',
            'auth-supported': 'none',
            'fsid': '6547bd3e-1397-11e2-82e5-53567c8d32dc',
            'monitor-secret': 'AQCXrnZQwI7KGBAAiPofmKEXKxu5bUzoYLVkbQ==',
        }

        # Include a non-existent device as osd-devices is a whitelist,
        # and this will catch cases where proposals attempt to change that.
        ceph_osd_config = {
            'osd-reformat': 'yes',
            'ephemeral-unmount': '/mnt',
            'osd-devices': '/dev/vdb /srv/ceph /dev/test-non-existent'
        }

        proxy_config = {
            'source': self.source
        }
        configs = {'ceph-mon': ceph_config,
                   'ceph-osd': ceph_osd_config,
                   'ceph-proxy': proxy_config}
        super(CephBasicDeployment, self)._configure_services(configs)

    def _configure_proxy(self):
        """Setup CephProxy with Ceph configuration
        from running Ceph cluster
        """
        mon_key = u.file_contents_safe(
            self.d.sentry['ceph-mon'][0],
            '/etc/ceph/ceph.client.admin.keyring'
        ).split(' = ')[-1].rstrip()

        ceph_ips = []
        for x in self.d.sentry['ceph-mon']:
            output, code = x.run("unit-get private-address")
            ceph_ips.append(output + ':6789')

        proxy_config = {
            'auth-supported': 'none',
            'admin-key': mon_key,
            'fsid': '6547bd3e-1397-11e2-82e5-53567c8d32dc',
            'monitor-hosts': ' '.join(ceph_ips)
        }
        u.log.debug('Config: {}'.format(proxy_config))
        self.d.configure('ceph-proxy', proxy_config)

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.ceph_osd_sentry = self.d.sentry['ceph-osd'][0]
        self.ceph0_sentry = self.d.sentry['ceph-mon'][0]
        self.radosgw_sentry = self.d.sentry['ceph-radosgw'][0]
        self.proxy_sentry = self.d.sentry['ceph-proxy'][0]

        u.log.debug('openstack release val: {}'.format(
            self._get_openstack_release()))
        u.log.debug('openstack release str: {}'.format(
            self._get_openstack_release_string()))

    def test_100_ceph_processes(self):
        """Verify that the expected service processes are running
        on each ceph unit."""

        # Process name and quantity of processes to expect on each unit
        ceph_processes = {
            'ceph-mon': 1,
        }

        # Units with process names and PID quantities expected
        expected_processes = {
            self.ceph0_sentry: ceph_processes
        }

        actual_pids = u.get_unit_process_ids(expected_processes)
        ret = u.validate_unit_process_ids(expected_processes, actual_pids)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

    def test_499_ceph_cmds_exit_zero(self):
        """Check basic functionality of ceph cli commands against
        ceph proxy units."""
        sentry_units = [
            self.proxy_sentry,
            self.ceph0_sentry
        ]
        commands = [
            'sudo ceph health',
            'sudo ceph mds stat',
            'sudo ceph pg stat',
            'sudo ceph osd stat',
            'sudo ceph mon stat',
        ]
        ret = u.check_commands_on_units(commands, sentry_units)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)
