# Overview

[Ceph][ceph-upstream] is a unified, distributed storage system designed for
excellent performance, reliability, and scalability.

The ceph-proxy charm deploys a proxy that acts as a [ceph-mon][ceph-mon-charm]
application for an external Ceph cluster. It joins a non-charmed Ceph cluster
to a Juju model.

# Usage

## Configuration

This section covers common and/or important configuration options. See file
`config.yaml` for the full list of options, along with their descriptions and
default values. See the [Juju documentation][juju-docs-config-apps] for details
on configuring applications.

#### `fsid`

The `fsid` option supplies the UUID of the external cluster.

#### `admin-key`

The `admin-key` option supplies the admin Cephx key of the external cluster.

#### `monitor-hosts`

The `monitor-hosts` option supplies the network addresses (and ports) of the
Monitors of the external cluster.

## Deployment

Let file ``ceph-proxy.yaml`` contain the deployment configuration:

```yaml
    ceph-proxy:
        fsid: a4f1fb08-c83d-11ea-8f4a-635b3b062931
        admin-key: AQCJvBFfWX+GLhAAln5dFd1rZekcGLyMmy58bQ==
        monitor-hosts: '10.246.114.21:6789 10.246.114.22:6789 10.246.114.7:6789'
```

To deploy:

    juju deploy --config ceph-proxy.yaml ceph-proxy

Now add relations as you normally would between a ceph-mon application and
another application, except substitute ceph-proxy for ceph-mon. For instance,
to use the external Ceph cluster as the backend for an existing glance
application:

    juju add-relation ceph-proxy:client glance:ceph

## Actions

Many of the ceph-mon charm's actions are supported. See file `actions.yaml` for
the full list of actions, along with their descriptions.

# Bugs

Please report bugs on [Launchpad][lp-bugs-charm-ceph-proxy].

For general charm questions refer to the [OpenStack Charm Guide][cg].

<!-- LINKS -->

[ceph-upstream]: https://ceph.io
[cg]: https://docs.openstack.org/charm-guide
[ceph-mon-charm]: https://jaas.ai/ceph-mon
[juju-docs-actions]: https://jaas.ai/docs/actions
[juju-docs-config-apps]: https://juju.is/docs/configuring-applications
[lp-bugs-charm-ceph-proxy]: https://bugs.launchpad.net/charm-ceph-proxy/+filebug
