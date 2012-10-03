
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

QUORUM = [ 'leader', 'peon' ] 

def is_quorum():
    cmd = [
        "ceph",
        "--admin-daemon",
	"/var/run/ceph/ceph-mon.%s.asok" % os.uname()[1],
        "mon_status"
        ]
    result = json.loads(subprocess.check_output(cmd))
    if result['state'] in QUORUM:
        return True
    else:
        return False

def wait_for_quorum():
    while not is_quorum():
        time.sleep(3)
