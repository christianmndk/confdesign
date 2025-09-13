#!/usr/bin/env python3
"""Calculate IPv4 subnet details.

This script accepts an IPv4 address and either a prefix length or a host
count. It prints the resulting network address, broadcast address and the
number of usable hosts in the subnet.

Examples:
    python subnet.py 192.168.1.5 --prefix 24
    python subnet.py 10.0.0.0 --hosts 50
"""

import argparse
import ipaddress
import math
import sys


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compute subnet information from an address and prefix length or host count."
    )
    parser.add_argument("address", help="IPv4 address or network address")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--prefix", type=int, help="Prefix length (0-32)")
    group.add_argument("-H", "--hosts", type=int, help="Desired number of hosts")
    return parser.parse_args()


def calculate_network(address: str, prefix: int | None, hosts: int | None) -> dict:
    """Return subnet information.

    Raises ValueError on invalid input.
    """
    try:
        ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError as exc:
        raise ValueError(f"Invalid IPv4 address: {address}") from exc

    if prefix is not None:
        if not (0 <= prefix <= 32):
            raise ValueError("Prefix length must be between 0 and 32.")
        network = ipaddress.IPv4Network(f"{address}/{prefix}", strict=False)
    else:
        if hosts is None or hosts <= 0:
            raise ValueError("Host count must be a positive integer.")
        if hosts > 4294967294:
            raise ValueError("Host count too large for IPv4.")
        host_bits = math.ceil(math.log2(hosts + 2))
        prefix = 32 - host_bits
        if prefix < 0:
            raise ValueError("Host count too large for IPv4.")
        network = ipaddress.IPv4Network(f"{address}/{prefix}", strict=False)

    usable_hosts = max(network.num_addresses - 2, 0)
    return {
        "network": str(network.network_address),
        "broadcast": str(network.broadcast_address),
        "prefix": network.prefixlen,
        "hosts": usable_hosts,
    }


def main() -> None:
    args = parse_args()
    try:
        result = calculate_network(args.address, args.prefix, args.hosts)
    except ValueError as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    print(f"Network:   {result['network']}/{result['prefix']}")
    print(f"Broadcast: {result['broadcast']}")
    print(f"Hosts:     {result['hosts']}")


if __name__ == "__main__":
    main()
