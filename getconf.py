#!/usr/bin/env python3
import argparse, getpass, pathlib, time, sys, re
from rich.progress import Progress, SpinnerColumn, TextColumn
from napalm import get_network_driver
import serial

PROMPT_RE = re.compile(r'[#>] ?$')

def ts(): return time.strftime("%Y%m%d-%H%M%S")
def write_file(path, text):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(text, encoding="utf-8")

def getconf_ssh(host, username, password, optional_args, include_running, progress):
    with progress:
        t = progress.add_task(f"[bold]SSH {host} → get_config", total=None)
        driver = get_network_driver("ios")
        dev = driver(hostname=host, username=username, password=password, optional_args=optional_args)
        dev.open()
        cfgs = dev.get_config(retrieve="all" if include_running else "startup")  # running/startup/candidate
        dev.close()
        progress.update(t, completed=1)
    out = []
    out.append(f"--- STARTUP ({ts()}) ---")
    out.append(cfgs.get("startup", "") or "")
    if include_running:
        out.append(f"\n--- RUNNING ({ts()}) ---")
        out.append(cfgs.get("running", "") or "")
    return "\n".join(out) + "\n"

def getconf_serial(com, baud, username, password, enable_secret, include_running, pace, progress):
    def send_read(ser, cmd):
        ser.write((cmd + "\r\n").encode()); time.sleep(pace)
        buf = bytearray()
        end = time.time() + 15
        while time.time() < end:
            chunk = ser.read(65535)
            if chunk:
                buf += chunk
                try:
                    if PROMPT_RE.search(buf.decode(errors="ignore")[-300:]): break
                except: pass
                end = time.time() + 2
            else:
                time.sleep(0.05)
        return buf.decode(errors="replace")

    with progress:
        t = progress.add_task(f"[bold]COM {com} → show config", total=None)
        ser = serial.Serial(com, baudrate=baud, timeout=0.7)
        time.sleep(pace); ser.reset_input_buffer()
        ser.write(b"\r\n"); time.sleep(pace)
        buf = ser.read(4096)
        if b"username" in buf.lower() and username:
            ser.write((username + "\r\n").encode()); time.sleep(pace); buf += ser.read(8192)
        if b"password" in buf.lower() and password:
            ser.write((password + "\r\n").encode()); time.sleep(pace); buf += ser.read(8192)
        ser.write(b"\r\n"); time.sleep(pace); buf += ser.read(4096)
        if b">" in buf and b"#" not in buf and enable_secret:
            ser.write(b"enable\r\n"); time.sleep(pace); buf += ser.read(4096)
            if b"password" in buf.lower():
                ser.write((enable_secret + "\r\n").encode()); time.sleep(pace); buf += ser.read(4096)
        ser.write(b"terminal length 0\r\n"); time.sleep(pace); ser.read(4096)

        startup = send_read(ser, "show startup-config")
        out = [f"--- STARTUP ({ts()}) ---", startup]
        if include_running:
            running = send_read(ser, "show running-config")
            out += [f"\n--- RUNNING ({ts()}) ---", running]
        ser.close()
        progress.update(t, completed=1)
    return "\n".join(out) + "\n"

def main():
    ap = argparse.ArgumentParser(prog="Getconf", description="Hent startup (og evt. running) via SSH (NAPALM) eller COM.")
    ap.add_argument("-c", action="store_true", help="Hent også running-config")
    ap.add_argument("-s","--ssh", help="IP/DNS (SSH)")
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("--com", help="COM-port (fx COM3)")
    ap.add_argument("-b","--baud", type=int, default=9600)
    ap.add_argument("-u","--user")
    ap.add_argument("-p","--pass")
    ap.add_argument("-e","--enable", help="Enable secret ved COM (SSH håndteres af NAPALM auto-privilege)")
    ap.add_argument("-f","--file", required=True)
    ap.add_argument("--pace", type=float, default=0.15, help="Delay pr. step på COM")
    args = ap.parse_args()

    if not args.ssh and not args.com:
        print("ERROR: angiv --ssh eller --com", file=sys.stderr); sys.exit(2)

    if args.ssh:
        if not args.user: args.user = input("SSH username: ").strip()
        if args.pass is None: args.pass = getpass.getpass("SSH password: ")
        optional_args = {"port": args.port}
        progress = Progress(SpinnerColumn(), TextColumn("{task.description}"))
        text = getconf_ssh(args.ssh, args.user, args.pass, optional_args, args.c, progress)
    else:
        pw = args.pass if args.pass is not None else (getpass.getpass("Console password (blank hvis ingen): ") or None)
        en = args.enable if args.enable is not None else (getpass.getpass("Enable secret (blank hvis ingen): ") or None)
        progress = Progress(SpinnerColumn(), TextColumn("{task.description}"))
        text = getconf_serial(args.com, args.baud, args.user, pw, en, args.c, args.pace, progress)

    write_file(args.file, text)
    print(f"OK: gemt -> {args.file}")

if __name__ == "__main__":
    import time
    main()
