import argparse, ipaddress, csv

def hosts_range(n):
    if n.prefixlen >= 31:
        return (None, None)
    return (n.network_address + 1, n.broadcast_address - 1)


def output_subnets(subnets, csv_path=None):
    header = ["#", "Subnet", "Network", "First usable", "Last usable", "Broadcast"]
    print(" | ".join(header))

    rows = []
    for i, n in enumerate(subnets):
        f, l = hosts_range(n)
        row = [
            str(i),
            str(n),
            str(n.network_address),
            str(f) if f is not None else "-",
            str(l) if l is not None else "-",
            str(n.broadcast_address),
        ]
        print(" | ".join(row))
        rows.append([i, str(n), str(n.network_address), f, l, str(n.broadcast_address)])

    if csv_path:
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for row in rows:
                w.writerow(row)
        print(f"CSV gemt: {csv_path}")

def main():
    p = argparse.ArgumentParser(description="Subnet calculator (IPv4)")
    p.add_argument("--base", "-b", required=True,
                   help="Base net i CIDR, fx 192.168.100.0/24")

    # Eksklusiv gruppe: enten prefix eller min-hosts
    g = p.add_mutually_exclusive_group()
    g.add_argument("-t", "--target-prefix", type=int,
                   help="Ny prefixlængde, fx 27 for /27")
    g.add_argument("-H", "--min-hosts", type=int,
                   help="Find mindste prefix der kan rumme antal hosts")

    p.add_argument("--vlsm", action="store_true",
                   help="Interaktiv VLSM-allokering af subnet")

    p.add_argument("--csv", help="Gem som CSV til fil")
    args = p.parse_args()

    base = ipaddress.ip_network(args.base, strict=True)

    if args.vlsm:
        if args.target_prefix is not None or args.min_hosts is not None:
            p.error("--vlsm kan ikke kombineres med --target-prefix eller --min-hosts")

        current_int = int(base.network_address)
        end_int = int(base.broadcast_address)
        subnets = []

        print("Indtast ønskede prefix-længder (tom linje afslutter):")
        while True:
            try:
                raw = input("Næste prefix (/xx eller tal): ").strip()
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print("\nAfbryder.")
                break

            if not raw:
                break

            if raw.startswith("/"):
                raw = raw[1:]

            try:
                prefix = int(raw)
            except ValueError:
                print("Ugyldigt prefix. Angiv et heltal mellem 0 og 32.")
                continue

            if prefix < base.prefixlen:
                print(f"Prefix /{prefix} er mindre end basens prefix /{base.prefixlen} og kan ikke ligge i {base}.")
                continue

            if prefix > 32:
                print("Prefix skal være mellem 0 og 32.")
                continue

            if current_int is None or current_int > end_int:
                print("Ingen adresser tilbage i basen.")
                continue

            current_addr = ipaddress.IPv4Address(current_int)
            net = ipaddress.ip_network((current_addr, prefix), strict=False)

            if net.network_address != current_addr:
                print(f"Kan ikke placere /{prefix} ved {current_addr}; ikke på netværksgrænse.")
                continue

            if int(net.broadcast_address) > end_int:
                print(f"Subnettet {net} passer ikke i {base}.")
                continue

            subnets.append(net)
            next_int = int(net.broadcast_address) + 1
            current_int = None if next_int > end_int else next_int

        if not subnets:
            print("Ingen subnet tildelt.")
            return

        print(f"Base: {base}  (VLSM) - Subnets: {len(subnets)}")
        output_subnets(subnets, args.csv)

        if current_int is None:
            remaining = 0
        else:
            remaining = int(base.broadcast_address) - current_int + 1

        if remaining:
            start_remain = ipaddress.IPv4Address(current_int)
            end_remain = base.broadcast_address
            print(f"Tilbage: {start_remain} - {end_remain} ({remaining} adresser)")
        else:
            print("Tilbage: 0 adresser")

        return

    if args.target_prefix is None and args.min_hosts is None:
        p.error("Angiv enten --target-prefix, --min-hosts eller brug --vlsm")

    if args.min_hosts:
        for hbits in range(1, 33 - base.prefixlen):
            if (2**hbits - 2) >= args.min_hosts:
                args.target_prefix = 32 - hbits
                break
        if args.target_prefix is None:
            p.error("Kan ikke finde et prefix der opfylder antallet af hosts i det angivne base-net.")

    subs = list(base.subnets(new_prefix=args.target_prefix))
    #print(f"Base: {base}  →  /{args.target_prefix}, Subnets: {len(subs)}")
    output_subnets(subs, args.csv)

if __name__ == "__main__":
    main()
