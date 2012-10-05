
#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  James Page <james.page@canonical.com>
#  Paul Collins <paul.collins@canonical.com>
#

import json
import subprocess
import time
import utils
import os

QUORUM = ['leader', 'peon']


def is_quorum():
    asok = "/var/run/ceph/ceph-mon.{}.asok".format(utils.get_unit_hostname())
    cmd = [
        "ceph",
        "--admin-daemon",
        asok,
        "mon_status"
        ]
    if os.path.exists(asok):
        try:
            result = json.loads(subprocess.check_output(cmd))
        except subprocess.CalledProcessError:
            return False
        except ValueError:
            # Non JSON response from mon_status
            return False
        if result['state'] in QUORUM:
            return True
        else:
            return False
    else:
        return False


def wait_for_quorum():
    while not is_quorum():
        time.sleep(3)


def add_bootstrap_hint(peer):
    asok = "/var/run/ceph/ceph-mon.{}.asok".format(utils.get_unit_hostname())
    cmd = [
        "ceph",
        "--admin-daemon",
        asok,
        "add_bootstrap_peer_hint",
        peer
        ]
    if os.path.exists(asok):
        # Ignore any errors for this call
        subprocess.call(cmd)


def is_osd_disk(dev):
    try:
        info = subprocess.check_output(['sgdisk', '-i', '1', dev])
        info = info.split("\n")
        for line in info:
            if line.startswith('Partition GUID code: 4FBD7E29-9D25-41B8-AFD0-062C0CEFF05D'):
                return True
    except subprocess.CalledProcessError:
        pass
    return False
