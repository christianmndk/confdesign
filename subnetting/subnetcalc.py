import argparse, ipaddress, csv

def hosts_range(n):
    if n.prefixlen >= 31:
        return (None, None)
    return (n.network_address + 1, n.broadcast_address - 1)

def main():
    p = argparse.ArgumentParser(description="Subnet calculator (IPv4)")
    p.add_argument("--base", "-b", required=True,
                   help="Base net i CIDR, fx 192.168.100.0/24")

    # Eksklusiv gruppe: enten prefix eller min-hosts
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("-t", "--target-prefix", type=int,
                   help="Ny prefixlængde, fx 27 for /27")
    g.add_argument("-H", "--min-hosts", type=int,
                   help="Find mindste prefix der kan rumme antal hosts")

    p.add_argument("--csv", help="Gem som CSV til fil")
    args = p.parse_args()

    base = ipaddress.ip_network(args.base, strict=True)

    if args.min_hosts:
        for hbits in range(1, 33 - base.prefixlen):
            if (2**hbits - 2) >= args.min_hosts:
                args.target_prefix = 32 - hbits
                break



    subs = list(base.subnets(new_prefix=args.target_prefix))
    print(f"Base: {base}  →  /{args.target_prefix}, Subnets: {len(subs)}")
    
    header = ["#", "Subnet", "Network", "First usable", "Last usable", "Broadcast"]
    rows = []
    
    for i, n in enumerate(subs):
        f, l = hosts_range(n)
        rows.append([str(i), str(n), str(n.network_address), str(f), str(l), str(n.broadcast_address)])
    
    # beregn bredde pr. kolonne (max længde i kolonnen)
    col_widths = [max(len(row[i]) for row in [header] + rows) for i in range(len(header))]
    
    # print header
    header_line = " | ".join(header[i].ljust(col_widths[i]) for i in range(len(header)))
    print(header_line)
    print("-+-".join("-" * w for w in col_widths))
    
    # print rækker
    for row in rows:
        line = " | ".join(row[i].ljust(col_widths[i]) for i in range(len(row)))
        print(line)
    
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f); w.writerow(header)
            for i, n in enumerate(subs):
                f,l = hosts_range(n)
                w.writerow([i, str(n), str(n.network_address), f, l, str(n.broadcast_address)])
        print(f"CSV gemt: {args.csv}")

if __name__ == "__main__":
    main()
