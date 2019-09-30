import collections
import subprocess
import unittest

import mock

import ceph


class CephTestCase(unittest.TestCase):
    def setUp(self):
        super(CephTestCase, self).setUp()

    @staticmethod
    def populated_config_side_effect(key):
        return {
            'user-keys':
            'client.cinder-ceph:AQAij2tbMNjMOhAAqInpXQLFrltDgmYid6KXbg== '
            'client.glance:AQCnjmtbuEACMxAA7joUmgLIGI4/3LKkPzUy8g== '
            'client.gnocchi:AQDk7qJb0csAFRAAQqPU6HchVW3PT6ymgXdI/A== '
            'client.nova-compute-kvm:'
            'AQBkjmtb1hWxLxAA3UhxSblgFSCtHVoZ8W6rNQ== '
            'client.radosgw.gateway:'
            'AQBljmtb65mrHhAAGy9VRkfsatWVLb9EpoWDfw==',
            'admin-user': 'client.myadmin'
        }[key]

    @staticmethod
    def empty_config_side_effect(key):
        return {
            'user-keys': '',
            'admin-user': 'client.myadmin'
        }[key]

    @mock.patch('ceph.config')
    def test_config_user_key_populated(self, mock_config):
        user_name = 'glance'
        user_key = 'AQCnjmtbuEACMxAA7joUmgLIGI4/3LKkPzUy8g=='

        mock_config.side_effect = self.populated_config_side_effect
        named_key = ceph._config_user_key(user_name)
        self.assertEqual(user_key, named_key)

    @mock.patch('ceph.config')
    def test_config_empty_user_key(self, mock_config):
        user_name = 'cinder-ceph'

        mock_config.side_effect = self.empty_config_side_effect
        named_key = ceph._config_user_key(user_name)
        self.assertEqual(named_key, None)

    @mock.patch.object(ceph, 'ceph_user')
    @mock.patch('subprocess.check_output')
    @mock.patch('ceph.config')
    def test_get_named_key_new(self, mock_config, mock_check_output,
                               mock_ceph_user):
        mock_ceph_user.return_value = 'ceph'
        user_name = 'cinder-ceph'
        expected_key = 'AQCnjmtbuEACMxAA7joUmgLIGI4/3LKkPzUy8g=='
        expected_output = ('[client.testuser]\n        key = {}'
                           .format(expected_key))

        def check_output_side_effect(cmd):
            if 'get-or-create' in cmd:
                return expected_output.encode('utf-8')
            else:
                raise subprocess.CalledProcessError(1, "")

        mock_config.side_effect = self.empty_config_side_effect
        mock_check_output.side_effect = check_output_side_effect
        named_key = ceph.get_named_key(user_name)
        print(named_key)

        self.assertEqual(expected_key, named_key)

    @mock.patch('subprocess.check_output')
    @mock.patch('ceph.get_unit_hostname')
    @mock.patch('ceph.ceph_user')
    @mock.patch('ceph.config')
    def test_get_named_key_existing(self, mock_config, mock_ceph_user,
                                    mock_get_unit_hostname, mock_check_output):
        user_name = 'cinder-ceph'
        expected_key = 'AQCnjmtbuEACMxAA7joUmgLIGI4/3LKkPzUy8g=='
        expected_output = ('[client.testuser]\n        key = {}'
                           .format(expected_key))
        caps = collections.OrderedDict([('mon', ['allow rw']),
                                        ('osd', ['allow rwx'])])
        ceph_user = 'ceph'
        ceph_proxy_host = 'cephproxy'
        mock_get_unit_hostname.return_value = ceph_proxy_host

        mock_check_output.return_value = expected_output.encode('utf-8')
        mock_config.side_effect = self.empty_config_side_effect
        mock_ceph_user.return_value = ceph_user
        named_key = ceph.get_named_key(user_name, caps)
        self.assertEqual(named_key, expected_key)
