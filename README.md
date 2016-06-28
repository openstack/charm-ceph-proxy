# Overview

Ceph is a distributed storage and network file system designed to provide
excellent performance, reliability, and scalability.

This charm allows connecting an existing Ceph deployment with a Juju environment.

# Usage

Your config.yaml needs to provide the  monitor-hosts and fsid options like below:

`config.yaml`:
```yaml
ceph-proxy:
   monitor-hosts: IP_ADDRESS:PORT IP ADDRESS:PORT
  fsid: FSID
```

You must then provide this configuration to the new deployment: `juju deploy ceph-proxy -c config.yaml`.

This charm noes NOT insert itself between the clusters, but merely makes the external cluster available through Juju's environment by exposing the same relations that the existing ceph charms do.

# Contact Information

## Authors 

- Chris MacNaughton <chris.macnaughton@canonical.com>

Report bugs on [Launchpad](http://bugs.launchpad.net/charms/+source/ceph-proxy/+filebug)

## Ceph

- [Ceph website](http://ceph.com)
- [Ceph mailing lists](http://ceph.com/resources/mailing-list-irc/)
- [Ceph bug tracker](http://tracker.ceph.com/projects/ceph)
