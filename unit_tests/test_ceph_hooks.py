from unittest import mock
import sys

# python-apt is not installed as part of test-requirements but is imported by
# some charmhelpers modules so create a fake import.
mock_apt = mock.MagicMock()
sys.modules['apt'] = mock_apt
mock_apt.apt_pkg = mock.MagicMock()

mock_apt_pkg = mock.MagicMock()
sys.modules['apt_pkg'] = mock_apt_pkg
mock_apt_pkg.upstream_version = mock.MagicMock()
mock_apt_pkg.upstream_version.return_value = '10.1.2-0ubuntu1'

import test_utils
import ceph_hooks as hooks

CEPH_KEY = 'AQDmP6dYWto6AhAAPKMkuvdFZYPRaiboU27IsA=='
CEPH_GET_KEY = """[client.admin]
        key = %s
        caps mds = "allow *"
        caps mon = "allow *"
        caps osd = "allow *"
""" % CEPH_KEY

TO_PATCH = [
    'config',
    'install_alternative',
    'mkdir',
    'related_units',
    'relation_get',
    'relation_ids',
    'relation_set',
    'remote_unit',
    'render',
    'service_name',
    'log'
]


def fake_log(message, level=None):
    print("juju-log %s: %s" % (level, message))


class TestHooks(test_utils.CharmTestCase):
    def setUp(self):
        super(TestHooks, self).setUp(hooks, TO_PATCH)
        self.service_name.return_value = 'ceph-service'
        self.config.side_effect = lambda x: self.test_config.get(x)
        self.remote_unit.return_value = 'client/0'
        self.log.side_effect = fake_log

    @mock.patch.object(hooks.ceph, 'ceph_user')
    @mock.patch.object(hooks, 'filter_installed_packages')
    @mock.patch('subprocess.check_output')
    @mock.patch('ceph_hooks.apt_install')
    def test_radosgw_relation(self, mock_apt_install, mock_check_output,
                              mock_filter_installed_packages, mock_ceph_user):
        mock_filter_installed_packages.return_value = []
        mock_ceph_user.return_value = 'ceph'
        settings = {'ceph-public-address': '127.0.0.1:1234 [::1]:4321',
                    'radosgw_key': CEPH_KEY,
                    'auth': 'cephx',
                    'fsid': 'some-fsid'}

        mock_check_output.return_value = CEPH_GET_KEY.encode()
        self.relation_get.return_value = {}
        self.test_config.set('monitor-hosts', settings['ceph-public-address'])
        self.test_config.set('fsid', settings['fsid'])
        self.test_config.set('admin-key', 'some-admin-key')
        hooks.radosgw_relation()
        self.relation_set.assert_called_with(relation_id=None,
                                             relation_settings=settings)
        mock_apt_install.assert_called_with(packages=[])

    @mock.patch('ceph.ceph_user')
    @mock.patch.object(hooks, 'radosgw_relation')
    @mock.patch.object(hooks, 'client_relation_joined')
    def test_emit_cephconf(self, mock_client_rel, mock_rgw_rel,
                           mock_ceph_user):
        mock_ceph_user.return_value = 'ceph-user'
        self.test_config.set('monitor-hosts', '127.0.0.1:1234')
        self.test_config.set('fsid', 'abc123')
        self.test_config.set('admin-key', 'key123')
        self.test_config.set('admin-user', 'client.myadmin')

        def c(k):
            x = {'radosgw': ['rados:1'],
                 'client': ['client:1'],
                 'rados:1': ['rados/1'],
                 'client:1': ['client/1'],
                 }
            return x[k]

        self.relation_ids.side_effect = c
        self.related_units.side_effect = c

        hooks.emit_cephconf()

        context = {'auth_supported': self.test_config.get('auth-supported'),
                   'mon_hosts': self.test_config.get('monitor-hosts'),
                   'fsid': self.test_config.get('fsid'),
                   'use_syslog': str(self.test_config.get(
                       'use-syslog')).lower(),
                   'loglevel': self.test_config.get('loglevel')}

        dirname = '/var/lib/charm/ceph-service'
        self.mkdir.assert_called_with(dirname, owner='ceph-user',
                                      group='ceph-user')
        self.render.assert_any_call('ceph.conf',
                                    '%s/ceph.conf' % dirname,
                                    context, perms=0o644)
        self.install_alternative.assert_called_with('ceph.conf',
                                                    '/etc/ceph/ceph.conf',
                                                    '%s/ceph.conf' % dirname,
                                                    100)
        keyring_template = 'ceph.keyring'
        keyring_name = 'ceph.{}.keyring'.format(
            self.test_config.get('admin-user'))
        context = {
            'admin_key': self.test_config.get('admin-key'),
            'admin_user': self.test_config.get('admin-user'),
        }
        self.render.assert_any_call(keyring_template,
                                    '/etc/ceph/' + keyring_name,
                                    context, owner='ceph-user', perms=0o600)

        mock_rgw_rel.assert_called_with(relid='rados:1', unit='rados/1')
        mock_client_rel.assert_called_with(relid='client:1', unit='client/1')

    @mock.patch.object(hooks.ceph, 'ceph_user')
    @mock.patch('subprocess.check_output')
    def test_client_relation_joined(self, mock_check_output, mock_ceph_user):
        mock_check_output.return_value = CEPH_GET_KEY.encode()
        mock_ceph_user.return_value = 'ceph'
        self.test_config.set('monitor-hosts', '127.0.0.1:1234')
        self.test_config.set('fsid', 'abc123')
        self.test_config.set('admin-key', 'some-admin-key')
        self.related_units.return_value = ['client/0']

        hooks.client_relation_joined('client:1')

        data = {'key': CEPH_KEY,
                'auth': 'cephx',
                'ceph-public-address': self.test_config.get('monitor-hosts')}

        self.relation_set.assert_called_with(relation_id='client:1',
                                             relation_settings=data)

    @mock.patch('ceph_hooks.emit_cephconf')
    @mock.patch('ceph_hooks.package_install')
    def test_config_get_skips_package_update(self,
                                             mock_package_install,
                                             mock_emit_cephconf):
        previous_test_config = test_utils.TestConfig()
        previous_test_config.set('source', 'distro')
        previous_test_config.set('key', '')
        previous = mock.MagicMock().return_value
        previous.previous.side_effect = lambda x: previous_test_config.get(x)
        self.config.side_effect = [previous, "distro", ""]
        hooks.config_changed()
        mock_package_install.assert_not_called()
        mock_emit_cephconf.assert_any_call()

    @mock.patch('ceph_hooks.emit_cephconf')
    @mock.patch('ceph_hooks.package_install')
    def test_update_apt_source(self, mock_package_install, mock_emit_cephconf):

        previous_test_config = test_utils.TestConfig()
        previous_test_config.set('source', 'distro')
        previous_test_config.set('key', '')
        previous = mock.MagicMock().return_value
        previous.previous.side_effect = lambda x: previous_test_config.get(x)
        self.config.side_effect = [previous, "cloud:cosmic-mimic", ""]
        hooks.config_changed()
        mock_package_install.assert_called_with()
        mock_emit_cephconf.assert_called_with()
