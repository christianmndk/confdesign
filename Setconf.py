#!/usr/bin/env python3
import argparse, getpass, pathlib, sys
from rich.console import Console
from rich.panel import Panel
from napalm import get_network_driver

console = Console()

def read_text(path): return pathlib.Path(path).read_text(encoding="utf-8")

def setconf_ssh(host, username, password, port, mode, filepath, auto_yes, rollback_on_error):
    driver = get_network_driver("ios")
    dev = driver(hostname=host, username=username, password=password, optional_args={"port": port})
    dev.open()
    try:
        if mode == "replace":
            dev.load_replace_candidate(filename=filepath)
        else:
            dev.load_merge_candidate(filename=filepath)
        diff = dev.compare_config() or ""
        if not diff.strip():
            console.print("[green]Ingen ændringer. Intet at committe.[/green]")
            dev.discard_config()
            return 0
        console.print(Panel.fit(diff, title="Diff", border_style="yellow"))
        if not auto_yes:
            ans = input("Commit? [y/N]: ").strip().lower()
            if ans != "y":
                dev.discard_config()
                console.print("[yellow]Afbrudt. Ingen ændringer gemt.[/yellow]")
                return 0
        dev.commit_config()
        console.print("[green]Commit OK. write mem håndteres af device/napalm.[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Fejl: {e}[/red]")
        if rollback_on_error:
            try:
                dev.rollback()
                console.print("[yellow]Rollback udført.[/yellow]")
            except Exception as e2:
                console.print(f"[red]Rollback fejlede: {e2}[/red]")
        return 2
    finally:
        dev.close()

def main():
    ap = argparse.ArgumentParser(prog="Setconf", description="Upload config via NAPALM (merge/replace med diff).")
    ap.add_argument("-s","--ssh", required=True, help="IP/DNS")
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("-u","--user", required=True)
    ap.add_argument("-p","--pass")
    ap.add_argument("-f","--file", required=True, help="Lokal configfil")
    ap.add_argument("-m","--mode", choices=["merge","replace"], default="merge")
    ap.add_argument("--yes", action="store_true", help="Commit uden prompt")
    ap.add_argument("--rollback", action="store_true", help="Rollback på fejl")
    args = ap.parse_args()

    if args.pass is None:
        args.pass = getpass.getpass("SSH password: ")

    rc = setconf_ssh(args.ssh, args.user, args.pass, args.port, args.mode, args.file, args.yes, args.rollback)
    sys.exit(rc)

if __name__ == "__main__":
    main()
