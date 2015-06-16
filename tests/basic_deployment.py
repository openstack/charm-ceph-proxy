#!/usr/bin/python

import amulet
import json
import time
from charmhelpers.contrib.openstack.amulet.deployment import (
    OpenStackAmuletDeployment
)
from charmhelpers.contrib.openstack.amulet.utils import (  # noqa
    OpenStackAmuletUtils,
    DEBUG,
    #ERROR
)

# Use DEBUG to turn on debug logging
u = OpenStackAmuletUtils(DEBUG)

# Resource names and constants
IMAGE_NAME = 'cirros-image-1'
POOLS = ['data', 'metadata', 'rbd', 'cinder', 'glance']
CINDER_POOL = 3
GLANCE_POOL = 4


class CephBasicDeployment(OpenStackAmuletDeployment):
    """Amulet tests on a basic ceph deployment."""

    def __init__(self, series=None, openstack=None, source=None, stable=False):
        """Deploy the entire test environment."""
        super(CephBasicDeployment, self).__init__(series, openstack, source,
                                                  stable)
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()
        self._initialize_tests()

    def _add_services(self):
        """Add services

           Add the services that we're testing, where ceph is local,
           and the rest of the service are from lp branches that are
           compatible with the local charm (e.g. stable or next).
           """
        this_service = {'name': 'ceph', 'units': 3}
        other_services = [{'name': 'mysql'},
                          {'name': 'keystone'},
                          {'name': 'rabbitmq-server'},
                          {'name': 'nova-compute'},
                          {'name': 'glance'},
                          {'name': 'cinder'}]
        super(CephBasicDeployment, self)._add_services(this_service,
                                                       other_services)

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'nova-compute:shared-db': 'mysql:shared-db',
            'nova-compute:amqp': 'rabbitmq-server:amqp',
            'nova-compute:image-service': 'glance:image-service',
            'nova-compute:ceph': 'ceph:client',
            'keystone:shared-db': 'mysql:shared-db',
            'glance:shared-db': 'mysql:shared-db',
            'glance:identity-service': 'keystone:identity-service',
            'glance:amqp': 'rabbitmq-server:amqp',
            'glance:ceph': 'ceph:client',
            'cinder:shared-db': 'mysql:shared-db',
            'cinder:identity-service': 'keystone:identity-service',
            'cinder:amqp': 'rabbitmq-server:amqp',
            'cinder:image-service': 'glance:image-service',
            'cinder:ceph': 'ceph:client'
        }
        super(CephBasicDeployment, self)._add_relations(relations)

    def _configure_services(self):
        """Configure all of the services."""
        keystone_config = {'admin-password': 'openstack',
                           'admin-token': 'ubuntutesting'}
        mysql_config = {'dataset-size': '50%'}
        cinder_config = {'block-device': 'None', 'glance-api-version': '2'}
        ceph_config = {
            'monitor-count': '3',
            'auth-supported': 'none',
            'fsid': '6547bd3e-1397-11e2-82e5-53567c8d32dc',
            'monitor-secret': 'AQCXrnZQwI7KGBAAiPofmKEXKxu5bUzoYLVkbQ==',
            'osd-reformat': 'yes',
            'ephemeral-unmount': '/mnt',
            'osd-devices': '/dev/vdb /srv/ceph'
        }

        configs = {'keystone': keystone_config,
                   'mysql': mysql_config,
                   'cinder': cinder_config,
                   'ceph': ceph_config}
        super(CephBasicDeployment, self)._configure_services(configs)

    def _initialize_tests(self):
        """Perform final initialization original tests get run."""
        # Access the sentries for inspecting service units
        self.mysql_sentry = self.d.sentry.unit['mysql/0']
        self.keystone_sentry = self.d.sentry.unit['keystone/0']
        self.rabbitmq_sentry = self.d.sentry.unit['rabbitmq-server/0']
        self.nova_sentry = self.d.sentry.unit['nova-compute/0']
        self.glance_sentry = self.d.sentry.unit['glance/0']
        self.cinder_sentry = self.d.sentry.unit['cinder/0']
        self.ceph0_sentry = self.d.sentry.unit['ceph/0']
        self.ceph1_sentry = self.d.sentry.unit['ceph/1']
        self.ceph2_sentry = self.d.sentry.unit['ceph/2']
        u.log.debug('openstack release val: {}'.format(
            self._get_openstack_release()))
        u.log.debug('openstack release str: {}'.format(
            self._get_openstack_release_string()))

        # Let things settle a bit original moving forward
        time.sleep(30)

        # Authenticate admin with keystone
        self.keystone = u.authenticate_keystone_admin(self.keystone_sentry,
                                                      user='admin',
                                                      password='openstack',
                                                      tenant='admin')
        # Authenticate admin with cinder endpoint
        self.cinder = u.authenticate_cinder_admin(self.keystone_sentry,
                                                  username='admin',
                                                  password='openstack',
                                                  tenant='admin')
        # Authenticate admin with glance endpoint
        self.glance = u.authenticate_glance_admin(self.keystone)

        # Authenticate admin with nova endpoint
        self.nova = u.authenticate_nova_user(self.keystone,
                                             user='admin',
                                             password='openstack',
                                             tenant='admin')

        # Create a demo tenant/role/user
        self.demo_tenant = 'demoTenant'
        self.demo_role = 'demoRole'
        self.demo_user = 'demoUser'
        if not u.tenant_exists(self.keystone, self.demo_tenant):
            tenant = self.keystone.tenants.create(tenant_name=self.demo_tenant,
                                                  description='demo tenant',
                                                  enabled=True)
            self.keystone.roles.create(name=self.demo_role)
            self.keystone.users.create(name=self.demo_user,
                                       password='password',
                                       tenant_id=tenant.id,
                                       email='demo@demo.com')

        # Authenticate demo user with keystone
        self.keystone_demo = u.authenticate_keystone_user(self.keystone,
                                                          self.demo_user,
                                                          'password',
                                                          self.demo_tenant)

        # Authenticate demo user with nova-api
        self.nova_demo = u.authenticate_nova_user(self.keystone,
                                                  self.demo_user,
                                                  'password',
                                                  self.demo_tenant)

    def _ceph_osd_id(self, index):
        """Produce a shell command that will return a ceph-osd id."""
        return "`initctl list | grep 'ceph-osd ' | awk 'NR=={} {{ print $2 }}' | grep -o '[0-9]*'`".format(index + 1)  # noqa

    def _ceph_df(self, sentry_unit):
        """Return dict of ceph df json output"""
        cmd = 'sudo ceph df --format=json'
        output, code = sentry_unit.run(cmd)
        if code != 0:
            msg = ('{} `{}` returned {} '
                   '{}'.format(sentry_unit.info['unit_name'],
                               cmd, code, output))
            u.log.debug(msg)
            amulet.raise_status(amulet.FAIL, msg=msg)

        df = json.loads(output)
        return df

    def _take_ceph_pool_sample(self, sentry_unit, pool_id=0):
        """Return ceph pool name, object count and disk space used
        for the specified pool ID number."""
        df = self._ceph_df(sentry_unit)
        pool_name = df['pools'][pool_id]['name']
        obj_count = df['pools'][pool_id]['stats']['objects']
        kb_used = df['pools'][pool_id]['stats']['kb_used']
        u.log.debug('Ceph {} pool (ID {}): {} objects, '
                    '{} kb used'.format(pool_name,
                                        pool_id,
                                        obj_count,
                                        kb_used))
        return pool_name, obj_count, kb_used

    def _validate_pool_samples(self, samples, resource_type="item",
                               sample_type="resource pool"):
        """Validate ceph pool samples taken over time, such as pool
        object counts or pool kb used, before adding, after adding, and
        after deleting items which affect those pool attributes."""
        original, created, deleted = range(3)

        if samples[created] <= samples[original] or \
                samples[deleted] >= samples[created]:
            msg = ('Ceph {} samples ({}) '
                   'unexpected.'.format(sample_type, samples))
            return msg
        else:
            u.log.debug('Ceph {} samples (OK): '
                        '{}'.format(sample_type, samples))
            return None

    def test_100_services(self):
        """Verify the expected services are running on the service units."""
        ceph_services = [
            'ceph-mon-all',
            'ceph-mon id=`hostname`',
            'ceph-osd-all',
            'ceph-osd id={}'.format(self._ceph_osd_id(0)),
            'ceph-osd id={}'.format(self._ceph_osd_id(1))
        ]

        services = {
            self.mysql_sentry: ['mysql'],
            self.rabbitmq_sentry: ['rabbitmq-server'],
            self.nova_sentry: ['nova-compute'],
            self.keystone_sentry: ['keystone'],
            self.glance_sentry: ['glance-registry',
                                 'glance-api'],
            self.cinder_sentry: ['cinder-api',
                                 'cinder-scheduler',
                                 'cinder-volume'],
            self.ceph0_sentry: ceph_services,
            self.ceph1_sentry: ceph_services,
            self.ceph2_sentry: ceph_services
        }

        ret = u.validate_services_by_name(services)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

    def test_200_ceph_nova_client_relation(self):
        """Verify the ceph to nova ceph-client relation data."""
        u.log.debug('Checking ceph:nova-compute ceph relation data...')
        unit = self.ceph0_sentry
        relation = ['client', 'nova-compute:ceph']
        expected = {
            'private-address': u.valid_ip,
            'auth': 'none',
            'key': u.not_null
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('ceph to nova ceph-client', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_201_nova_ceph_client_relation(self):
        """Verify the nova to ceph client relation data."""
        u.log.debug('Checking nova-compute:ceph ceph-client relation data...')
        unit = self.nova_sentry
        relation = ['ceph', 'ceph:client']
        expected = {
            'private-address': u.valid_ip
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('nova to ceph ceph-client', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_202_ceph_glance_client_relation(self):
        """Verify the ceph to glance ceph-client relation data."""
        u.log.debug('Checking ceph:glance client relation data...')
        unit = self.ceph1_sentry
        relation = ['client', 'glance:ceph']
        expected = {
            'private-address': u.valid_ip,
            'auth': 'none',
            'key': u.not_null
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('ceph to glance ceph-client', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_203_glance_ceph_client_relation(self):
        """Verify the glance to ceph client relation data."""
        u.log.debug('Checking glance:ceph client relation data...')
        unit = self.glance_sentry
        relation = ['ceph', 'ceph:client']
        expected = {
            'private-address': u.valid_ip
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('glance to ceph ceph-client', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_204_ceph_cinder_client_relation(self):
        """Verify the ceph to cinder ceph-client relation data."""
        u.log.debug('Checking ceph:cinder ceph relation data...')
        unit = self.ceph2_sentry
        relation = ['client', 'cinder:ceph']
        expected = {
            'private-address': u.valid_ip,
            'auth': 'none',
            'key': u.not_null
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('ceph to cinder ceph-client', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_205_cinder_ceph_client_relation(self):
        """Verify the cinder to ceph ceph-client relation data."""
        u.log.debug('Checking cinder:ceph ceph relation data...')
        unit = self.cinder_sentry
        relation = ['ceph', 'ceph:client']
        expected = {
            'private-address': u.valid_ip
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('cinder to ceph ceph-client', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_300_ceph_config(self):
        """Verify the data in the ceph config file."""
        u.log.debug('Checking ceph config file data...')
        unit = self.ceph0_sentry
        conf = '/etc/ceph/ceph.conf'
        expected = {
            'global': {
                'keyring': '/etc/ceph/$cluster.$name.keyring',
                'fsid': '6547bd3e-1397-11e2-82e5-53567c8d32dc',
                'log to syslog': 'false',
                'err to syslog': 'false',
                'clog to syslog': 'false',
                'mon cluster log to syslog': 'false',
                'auth cluster required': 'none',
                'auth service required': 'none',
                'auth client required': 'none'
            },
            'mon': {
                'keyring': '/var/lib/ceph/mon/$cluster-$id/keyring'
            },
            'mds': {
                'keyring': '/var/lib/ceph/mds/$cluster-$id/keyring'
            },
            'osd': {
                'keyring': '/var/lib/ceph/osd/$cluster-$id/keyring',
                'osd journal size': '1024',
                'filestore xattr use omap': 'true'
            },
        }

        for section, pairs in expected.iteritems():
            ret = u.validate_config_data(unit, conf, section, pairs)
            if ret:
                message = "ceph config error: {}".format(ret)
                amulet.raise_status(amulet.FAIL, msg=message)

    def test_302_cinder_rbd_config(self):
        """Verify the cinder config file data regarding ceph."""
        u.log.debug('Checking cinder (rbd) config file data...')
        unit = self.cinder_sentry
        conf = '/etc/cinder/cinder.conf'
        expected = {
            'DEFAULT': {
                'volume_driver': 'cinder.volume.drivers.rbd.RBDDriver'
            }
        }
        for section, pairs in expected.iteritems():
            ret = u.validate_config_data(unit, conf, section, pairs)
            if ret:
                message = "cinder (rbd) config error: {}".format(ret)
                amulet.raise_status(amulet.FAIL, msg=message)

    def test_304_glance_rbd_config(self):
        """Verify the glance config file data regarding ceph."""
        u.log.debug('Checking glance (rbd) config file data...')
        unit = self.glance_sentry
        conf = '/etc/glance/glance-api.conf'
        expected = {
            'DEFAULT': {
                'default_store': 'rbd',
                'rbd_store_ceph_conf': '/etc/ceph/ceph.conf',
                'rbd_store_user': 'glance',
                'rbd_store_pool': 'glance',
                'rbd_store_chunk_size': '8'
            }
        }
        for section, pairs in expected.iteritems():
            ret = u.validate_config_data(unit, conf, section, pairs)
            if ret:
                message = "glance (rbd) config error: {}".format(ret)
                amulet.raise_status(amulet.FAIL, msg=message)

    def test_306_nova_rbd_config(self):
        """Verify the nova config file data regarding ceph."""
        u.log.debug('Checking nova (rbd) config file data...')
        unit = self.nova_sentry
        conf = '/etc/nova/nova.conf'
        expected = {
            'libvirt': {
                'rbd_pool': 'nova',
                'rbd_user': 'nova-compute',
                'rbd_secret_uuid': u.not_null
            }
        }
        for section, pairs in expected.iteritems():
            ret = u.validate_config_data(unit, conf, section, pairs)
            if ret:
                message = "nova (rbd) config error: {}".format(ret)
                amulet.raise_status(amulet.FAIL, msg=message)

    def test_400_ceph_check_osd_pools(self):
        """Check osd pools on all ceph units, expect them to be
        identical, and expect specific pools to be present."""
        u.log.debug('Checking pools on ceph units...')

        cmd = 'sudo ceph osd lspools'
        results = []
        sentries = [
            self.ceph0_sentry,
            self.ceph1_sentry,
            self.ceph2_sentry
        ]

        for sentry_unit in sentries:
            output, code = sentry_unit.run(cmd)
            results.append(output)
            msg = ('{} `{}` returned {} '
                   '{}'.format(sentry_unit.info['unit_name'],
                               cmd, code, output))
            u.log.debug(msg)
            if code != 0:
                amulet.raise_status(amulet.FAIL, msg=msg)

            # Check for presence of all pools on this unit
            for pool in POOLS:
                if pool not in output:
                    msg = ('{} does not have pool: '
                           '{}'.format(sentry_unit.info['unit_name'], pool))
                    amulet.raise_status(amulet.FAIL, msg=msg)
            u.log.debug('{} has the expected '
                        'pools.'.format(sentry_unit.info['unit_name']))

        # Check that lspool produces the same output on all units
        if len(set(results)) == 1:
            u.log.debug('Pool list on all ceph units produced the '
                        'same results (OK).')
        else:
            u.log.debug('Pool list results: {}'.format(results))
            msg = 'Pool list results are not identical on all ceph units.'
            amulet.raise_status(amulet.FAIL, msg=msg)

    def test_410_ceph_cinder_vol_create(self):
        """Create and confirm a ceph-backed cinder volume, and inspect
        ceph cinder pool object count as the volume is created
        and deleted."""
        sentry_unit = self.ceph0_sentry
        obj_count_samples = []
        pool_size_samples = []

        # Check ceph cinder pool object count, disk space usage and pool name
        u.log.debug('Checking ceph cinder pool original samples...')
        pool_name, obj_count, kb_used = self._take_ceph_pool_sample(
            sentry_unit, pool_id=CINDER_POOL)
        obj_count_samples.append(obj_count)
        pool_size_samples.append(kb_used)

        expected = 'cinder'
        if pool_name != expected:
            msg = ('Ceph pool {} unexpected name (actual, expected): '
                   '{}. {}'.format(CINDER_POOL, pool_name, expected))
            amulet.raise_status(amulet.FAIL, msg=msg)

        # Create ceph-backed cinder volume
        cinder_vol = u.create_cinder_volume(self.cinder)

        # Re-check ceph cinder pool object count and disk usage
        time.sleep(10)
        u.log.debug('Checking ceph cinder pool samples after volume create...')
        pool_name, obj_count, kb_used = self._take_ceph_pool_sample(
            sentry_unit, pool_id=CINDER_POOL)
        obj_count_samples.append(obj_count)
        pool_size_samples.append(kb_used)

        # Delete ceph-backed cinder volume
        u.delete_resource(self.cinder.volumes, cinder_vol, msg="cinder volume")

        # Final check, ceph cinder pool object count and disk usage
        time.sleep(10)
        u.log.debug('Checking ceph cinder pool after volume delete...')
        pool_name, obj_count, kb_used = self._take_ceph_pool_sample(
            sentry_unit, pool_id=CINDER_POOL)
        obj_count_samples.append(obj_count)
        pool_size_samples.append(kb_used)

        # Validate ceph cinder pool object count samples over time
        ret = self._validate_pool_samples(samples=obj_count_samples,
                                          resource_type="cinder volume",
                                          sample_type="pool object count")
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

        # Validate ceph cinder pool disk space usage samples over time
        ret = self._validate_pool_samples(samples=pool_size_samples,
                                          resource_type="cinder volume",
                                          sample_type="pool disk usage size")
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

    def test_412_ceph_glance_image_create_delete(self):
        """Create and confirm a ceph-backed glance image, and inspect
        ceph glance pool object count as the image is created
        and deleted."""
        sentry_unit = self.ceph0_sentry
        obj_count_samples = []
        pool_size_samples = []

        # Check ceph glance pool object count, disk space usage and pool name
        u.log.debug('Checking ceph glance pool original samples...')
        pool_name, obj_count, kb_used = self._take_ceph_pool_sample(
            sentry_unit, pool_id=GLANCE_POOL)
        obj_count_samples.append(obj_count)
        pool_size_samples.append(kb_used)

        expected = 'glance'
        if pool_name != expected:
            msg = ('Ceph glance pool {} unexpected name (actual, '
                   'expected): {}. {}'.format(GLANCE_POOL,
                                              pool_name, expected))
            amulet.raise_status(amulet.FAIL, msg=msg)

        # Create ceph-backed glance image
        glance_img = u.create_cirros_image(self.glance, IMAGE_NAME)

        # Re-check ceph glance pool object count and disk usage
        time.sleep(10)
        u.log.debug('Checking ceph glance pool samples after image create...')
        pool_name, obj_count, kb_used = self._take_ceph_pool_sample(
            sentry_unit, pool_id=GLANCE_POOL)
        obj_count_samples.append(obj_count)
        pool_size_samples.append(kb_used)

        # Delete ceph-backed glance image
        u.delete_resource(self.glance.images,
                          glance_img, msg="glance image")

        # Final check, ceph glance pool object count and disk usage
        time.sleep(10)
        u.log.debug('Checking ceph glance pool samples after image delete...')
        pool_name, obj_count, kb_used = self._take_ceph_pool_sample(
            sentry_unit, pool_id=GLANCE_POOL)
        obj_count_samples.append(obj_count)
        pool_size_samples.append(kb_used)

        # Validate ceph glance pool object count samples over time
        ret = self._validate_pool_samples(samples=obj_count_samples,
                                          resource_type="glance image",
                                          sample_type="pool object count")
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

        # Validate ceph glance pool disk space usage samples over time
        ret = self._validate_pool_samples(samples=pool_size_samples,
                                          resource_type="glance image",
                                          sample_type="pool disk usage size")
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

    def test_499_ceph_cmds_exit_zero(self):
        """Check that all ceph commands in a list return zero on all
        ceph units listed."""
        sentry_units = [
            self.ceph0_sentry,
            self.ceph1_sentry,
            self.ceph2_sentry
        ]
        commands = [
            'sudo ceph -s',
            'sudo ceph health',
            'sudo ceph mds stat',
            'sudo ceph pg stat',
            'sudo ceph osd stat',
            'sudo ceph mon stat',
            'sudo ceph osd pool get data size',
            'sudo ceph osd pool get data pg_num',
        ]
        ret = u.check_commands_on_units(commands, sentry_units)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

    # FYI: No restart check as ceph services do not restart
    # when charm config changes, unless monitor count increases.
