import mock
import unittest

import ceph_broker


class CephBrokerTestCase(unittest.TestCase):

    def setUp(self):
        super(CephBrokerTestCase, self).setUp()

    @mock.patch('ceph_broker.log')
    def test_process_requests_noop(self, mock_log):
        rc = ceph_broker.process_requests([{}])
        self.assertEqual(rc, 1)

    @mock.patch('ceph_broker.log')
    def test_process_requests_invalid(self, mock_log):
        rc = ceph_broker.process_requests([{'op': 'invalid_op'}])
        self.assertEqual(rc, 1)

    @mock.patch('ceph_broker.create_pool')
    @mock.patch('ceph_broker.pool_exists')
    @mock.patch('ceph_broker.log')
    def test_process_requests_create_pool(self, mock_log, mock_pool_exists,
                                          mock_create_pool):
        mock_pool_exists.return_value = False
        rc = ceph_broker.process_requests([{'op': 'create_pool', 'name': 'foo',
                                            'replicas': 3}])
        mock_pool_exists.assert_called_with(service='admin', name='foo')
        mock_create_pool.assert_called_with(service='admin', name='foo',
                                            replicas=3)
        self.assertEqual(rc, 0)

    @mock.patch('ceph_broker.create_pool')
    @mock.patch('ceph_broker.pool_exists')
    @mock.patch('ceph_broker.log')
    def test_process_requests_create_pool_exists(self, mock_log,
                                                 mock_pool_exists,
                                                 mock_create_pool):
        mock_pool_exists.return_value = True
        rc = ceph_broker.process_requests([{'op': 'create_pool', 'name': 'foo',
                                            'replicas': 3}])
        mock_pool_exists.assert_called_with(service='admin', name='foo')
        self.assertFalse(mock_create_pool.called)
        self.assertEqual(rc, 0)
