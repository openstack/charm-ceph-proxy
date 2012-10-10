Overview
========

Ceph is a distributed storage and network file system designed to provide
excellent performance, reliability, and scalability.

This charm deploys a Ceph cluster.

Usage
=====

The ceph charm has two pieces of mandatory configuration for which no defaults
are provided:

    fsid:
        uuid specific to a ceph cluster used to ensure that different
        clusters don't get mixed up - use `uuid` to generate one.
             
    monitor-secret: 
        a ceph generated key used by the daemons that manage to cluster
        to control security.  You can use the ceph-authtool command to 
        generate one:
          
            ceph-authtool /dev/stdout --name=mon. --gen-key
              
These two pieces of configuration must NOT be changed post bootstrap; attempting
todo this will cause a reconfiguration error and new service units will not join
the existing ceph cluster.
        
The charm also supports specification of the storage devices to use in the ceph
cluster.

    osd-devices:
        A list of devices that the charm will attempt to detect, initialise and
        activate as ceph storage.
        
        This this can be a superset of the actual storage devices presented to
        each service unit and can be changed post ceph bootstrap using `juju set`.
        
At a minimum you must provide a juju config file during initial deployment
with the fsid and monitor-secret options (contents of cepy.yaml below):

    ceph:
        fsid: ecbb8960-0e21-11e2-b495-83a88f44db01 
        monitor-secret: AQD1P2xQiKglDhAA4NGUF5j38Mhq56qwz+45wg==
        osd-devices: /dev/vdb /dev/vdc /dev/vdd /dev/vde
        
Specifying the osd-devices to use is also a good idea.

Boot things up by using:

    juju deploy -n 3 --config ceph.yaml ceph

By default the ceph cluster will not bootstrap until 3 service units have been
deployed and started; this is to ensure that a quorum is achieved prior to adding
storage devices.

Contact Information
===================

Author: Paul Collins <paul.collins@canonical.com>,
 James Page <james.page@ubuntu.com>
Report bugs at: http://bugs.launchpad.net/charms/+source/ceph/+filebug
Location: http://jujucharms.com/charms/ceph
    
Technical Bootnotes
===================

This charm is currently deliberately inflexible and potentially destructive.
It is designed to deploy on exactly three machines. Each machine will run mon
and osd.

This charm uses the new-style Ceph deployment as reverse-engineered from the
Chef cookbook at https://github.com/ceph/ceph-cookbooks, although we selected
a different strategy to form the monitor cluster.  Since we don't know the
names *or* addresses of the machines in advance, we use the relation-joined
hook to wait for all three nodes to come up, and then write their addresses
to ceph.conf in the "mon host" parameter. After we initialize the monitor
cluster a quorum forms quickly, and OSD bringup proceeds.

The osds use so-called "OSD hotplugging".  ceph-disk-prepare is used to create
the filesystems with a special GPT partition type.  udev is set up to mounti
such filesystems and start the osd daemons as their storage becomes visible to
the system (or after "udevadm trigger").

The Chef cookbook above performs some extra steps to generate an OSD
bootstrapping key and propagate it to the other nodes in the cluster. Since
all OSDs run on nodes that also run mon, we don't need this and did not
implement it.

See http://ceph.com/docs/master/dev/mon-bootstrap/ for more information on Ceph
monitor cluster deployment strategies and pitfalls. 
