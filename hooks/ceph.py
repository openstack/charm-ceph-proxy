
#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  James Page <james.page@canonical.com>
#

import subprocess
import json
import os

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
