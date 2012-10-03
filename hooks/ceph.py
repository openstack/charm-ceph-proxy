
#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  James Page <james.page@canonical.com>
#  Paul Collins <paul.collins@canonical.com>
#

import json
import os
import subprocess
import time
import utils

QUORUM = [ 'leader', 'peon' ]

def is_quorum():
    cmd = [
        "ceph",
        "--admin-daemon",
        "/var/run/ceph/ceph-mon.%s.asok" % utils.get_unit_hostname(),
        "mon_status"
        ]

    try:
        result = json.loads(subprocess.check_output(cmd))
    except subprocess.CalledProcessError:
        return False

    if result['state'] in QUORUM:
        return True
    else:
        return False

def wait_for_quorum():
    while not is_quorum():
        time.sleep(3)
