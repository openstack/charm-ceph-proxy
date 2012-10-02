#!/usr/bin/python

#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  Paul Collins <paul.collins@canonical.com>
#

import os
import subprocess
import sys

def install():
    print "install"

def config_changed():
    print "config_changed"

def mon_relation():
    print "mon_relation"

hooks = {
    'mon-relation-joined': mon_relation,
    'mon-relation-changed': mon_relation,
    'mon-relation-departed': mon_relation,
    'install': install,
    'config-changed': config_changed,
}

hook = os.path.basename(sys.argv[0])

try:
    hooks[hook]()
except:
    subprocess.call(['juju-log', '-l', 'INFO',
                     "This charm doesn't know how to handle '%s'." % hook])

sys.exit(0)
