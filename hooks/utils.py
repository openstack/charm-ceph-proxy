
#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  James Page <james.page@ubuntu.com>
#  Paul Collins <paul.collins@canonical.com>
#

import socket
import re
from charmhelpers.core.hookenv import (
    unit_get,
    cached,
    config
)
from charmhelpers.fetch import (
    apt_install,
    filter_installed_packages
)

from charmhelpers.core.host import (
    lsb_release
)

from charmhelpers.contrib.network import ip
from charmhelpers.contrib.network.ip import (
    is_ipv6,
    get_ipv6_addr
)

TEMPLATES_DIR = 'templates'

try:
    import jinja2
except ImportError:
    apt_install(filter_installed_packages(['python-jinja2']),
                fatal=True)
    import jinja2

try:
    import dns.resolver
except ImportError:
    apt_install(filter_installed_packages(['python-dnspython']),
                fatal=True)
    import dns.resolver


def render_template(template_name, context, template_dir=TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)


def enable_pocket(pocket):
    apt_sources = "/etc/apt/sources.list"
    with open(apt_sources, "r") as sources:
        lines = sources.readlines()
    with open(apt_sources, "w") as sources:
        for line in lines:
            if pocket in line:
                sources.write(re.sub('^# deb', 'deb', line))
            else:
                sources.write(line)


@cached
def get_unit_hostname():
    return socket.gethostname()


@cached
def get_host_ip(hostname=None):
    hostname = hostname or unit_get('private-address')
    try:
        # Test to see if already an IPv4 address
        socket.inet_aton(hostname)
        return hostname
    except socket.error:
        # This may throw an NXDOMAIN exception; in which case
        # things are badly broken so just let it kill the hook
        answers = dns.resolver.query(hostname, 'A')
        if answers:
            return answers[0].address


@cached
def get_public_addr():
    addr = config('ceph-public-network')
    if config('prefer-ipv6'):
        if addr and is_ipv6(addr):
            return addr
        else:
            return get_ipv6_addr()
    else:
        return ip.get_address_in_network(addr, fallback=get_host_ip())


def setup_ipv6():
    ubuntu_rel = float(lsb_release()['DISTRIB_RELEASE'])
    if ubuntu_rel < 14.04:
        raise Exception("IPv6 is not supported for Ubuntu "
                        "versions less than Trusty 14.04")
