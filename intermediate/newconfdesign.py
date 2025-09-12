# ConfDesign.py
# TUI config generator med frie (custom) VLANs – kun MGMT er tvunget.
# Windows: pip install windows-curses

import curses, json, os
from datetime import datetime, timezone

KEY_ENTER = [10, 13]
PROFILE_FILE = "profiles.json"

# ==================== TUI widgets ====================
def center_text(win, y, text, attr=0):
    h, w = win.getmaxyx(); x = max(0, (w - len(text)) // 2)
    win.addstr(y, x, text[:w-1], attr)

def draw_box(win, title=None):
    win.box(); 
    if title: win.addstr(0, 2, f" {title} ")

def menu(win, title, options, footer="↑↓ vælg  •  Enter ok  •  q tilbage", start_index=0):
    curses.curs_set(0); idx = start_index
    while True:
        win.clear(); draw_box(win, title); h, w = win.getmaxyx()
        for i, opt in enumerate(options):
            y = 2 + i; sel = (i == idx); pre = "➤ " if sel else "  "
            win.addstr(y, 2, f"{pre}{opt}"[:w-4], curses.A_REVERSE if sel else curses.A_NORMAL)
        win.addstr(h-2, 2, footer[:w-4], curses.A_DIM); win.refresh()
        c = win.getch()
        if c in (curses.KEY_UP, ord('k')): idx = (idx - 1) % len(options)
        elif c in (curses.KEY_DOWN, ord('j')): idx = (idx + 1) % len(options)
        elif c in KEY_ENTER: return idx
        elif c in (ord('q'), 27): return None

def checkbox_menu(win, title, items, footer="Space=flueben  •  a=alle/ingen  •  Enter=ok  •  F10=skip  •  q=tilbage"):
    curses.curs_set(0); idx=0
    labels=[l for l,_ in items]; states=[d for _,d in items]
    while True:
        win.clear(); draw_box(win,title); h,w=win.getmaxyx()
        for i,lbl in enumerate(labels):
            y=2+i; sel=(i==idx); box="[x]" if states[i] else "[ ]"; pre="➤ " if sel else "  "
            win.addstr(y,2,f"{pre}{box} {lbl}"[:w-4], curses.A_REVERSE if sel else curses.A_NORMAL)
        win.addstr(h-2,2,footer[:w-4],curses.A_DIM); win.refresh()
        c=win.getch()
        if c in (curses.KEY_UP, ord('k')): idx=(idx-1)%len(labels)
        elif c in (curses.KEY_DOWN, ord('j')): idx=(idx+1)%len(labels)
        elif c==ord(' '): states[idx]=not states[idx]
        elif c==ord('a'): states=[not any(states)]*len(states)
        elif c==curses.KEY_F10: return "__SKIP_ROLE__"
        elif c in KEY_ENTER: return {labels[i]: states[i] for i in range(len(labels))}
        elif c in (ord('q'),27): return None

def text_input(win, title, fields):
    curses.curs_set(1); idx=0
    vals=[str(d) if d is not None else "" for _,d,_ in fields]
    while True:
        win.clear(); draw_box(win,title); h,w=win.getmaxyx()
        for i,(lbl,_d,_v) in enumerate(fields):
            sel=(i==idx); pre="➤ " if sel else "  "
            win.addstr(2+i,2,f"{pre}{lbl}: {vals[i]}"[:w-4], curses.A_REVERSE if sel else curses.A_NORMAL)
        win.addstr(h-2,2,"Enter=edit/næste  •  ↑↓  •  F10=færdig  •  ESC=tilbage",curses.A_DIM); win.refresh()
        c=win.getch()
        if c in (curses.KEY_UP, ord('k')): idx=(idx-1)%len(fields)
        elif c in (curses.KEY_DOWN, ord('j')): idx=(idx+1)%len(fields)
        elif c==27: return None
        elif c==curses.KEY_F10: return {fields[i][0]: vals[i] for i in range(len(fields))}
        elif c in KEY_ENTER:
            curses.echo()
            prompt=f"➤ {fields[idx][0]}: "
            win.addstr(2+idx,2," "*(w-4)); win.addstr(2+idx,2,prompt); win.refresh()
            s=win.getstr(2+idx,2+len(prompt),w-10).decode('utf-8').strip()
            curses.noecho()
            if s!="":
                val=fields[idx][2]; ok,msg=(val(s) if val else (True,""))
                if ok: vals[idx]=s
                else: _toast(win,f"Ugyldig: {msg}")

def _toast(win, msg, ms=1200):
    h,w=win.getmaxyx(); bw=min(w-4,max(30,len(msg)+6)); bh=5
    y=(h-bh)//2; x=(w-bw)//2; sub=win.subwin(bh,bw,y,x); sub.box()
    center_text(sub,2,msg); win.refresh(); curses.napms(ms)

def show_preview(stdscr, text, title="Forhåndsvisning"):
    lines=text.splitlines(); top=0; curses.curs_set(0)
    while True:
        stdscr.clear(); draw_box(stdscr,title+"  •  PgUp/PgDn/↑↓  •  q=tilbage"); h,w=stdscr.getmaxyx()
        avail=h-4
        for i in range(avail):
            j=top+i
            if j>=len(lines): break
            stdscr.addstr(2+i,2,lines[j][:w-4])
        stdscr.refresh()
        c=stdscr.getch()
        if c in (ord('q'),27): return
        elif c==curses.KEY_DOWN and top+avail<len(lines): top+=1
        elif c==curses.KEY_UP and top>0: top-=1
        elif c==curses.KEY_NPAGE: top=min(top+avail,max(0,len(lines)-avail))
        elif c==curses.KEY_PPAGE: top=max(0,top-avail)

# ==================== Validators ====================
def not_empty(v): return (len(v.strip())>0, "må ikke være tom")
def vlan_id(v):
    try: i=int(v); return (1<=i<=4094, "1–4094")
    except: return (False,"heltal 1–4094")
def ipv4_addr(v):
    parts=v.split('.'); ok=len(parts)==4 and all(s.isdigit() and 0<=int(s)<=255 for s in parts)
    return (ok,"fx 192.168.10.0")
def prefix_validator(v):
    try: p=int(v); return (0<=p<=32,"0–32")
    except: return (False,"0–32")
def host_octet_range(maxhosts):
    def _v(v):
        try: i=int(v); return (1<=i<=maxhosts-1, f"1–{maxhosts-1}")
        except: return (False, f"1–{maxhosts-1}")
    return _v
def int_range(lo,hi):
    def _v(v):
        try: i=int(v); return (lo<=i<=hi, f"{lo}–{hi}")
        except: return (False, f"heltal {lo}–{hi}")
    return _v
def iface_prefix_ok(v):
    ok=v.endswith("/") and any(v.lower().startswith(x) for x in ("fa","fastethernet","gi","gigabitethernet","te","tengigabitethernet"))
    return (ok,"fx FastEthernet0/  eller  GigabitEthernet0/")

# ==================== IP helpers ====================
def ip_to_int(ip):
    a,b,c,d=map(int,ip.split('.')); return (a<<24)|(b<<16)|(c<<8)|d
def int_to_ip(n):
    return ".".join(str((n>>i)&0xff) for i in (24,16,8,0))
def mask_from_prefix(p):
    v=(0xffffffff << (32-p)) & 0xffffffff if p>0 else 0
    return int_to_ip(v)

# ==================== Profile storage ====================
DEFAULT_PROFILE = {
    "name": "basic-office",
    "vlans": {
        "mgmt": {"id":10,"name":"MGMT","net":"192.168.10.0","prefix":24,"gw_host":1,"svi_host":2,"purpose":"mgmt"},
        # resten er nu “custom” og oprettes i UI
    }
}

def load_profiles():
    if not os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE,"w",encoding="utf-8") as f: json.dump([DEFAULT_PROFILE], f, indent=2)
        return [DEFAULT_PROFILE]
    with open(PROFILE_FILE,"r",encoding="utf-8") as f:
        try: return json.load(f)
        except: return [DEFAULT_PROFILE]

def save_profiles(profs):
    with open(PROFILE_FILE,"w",encoding="utf-8") as f: json.dump(profs, f, indent=2)

def slugify(name):
    s="".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    return s or "vlan"

# ==================== VLAN editor (custom list) ====================
PURPOSES = ["general","access-default","printer","voice","guest"]

def edit_mgmt(stdscr, mgmt):
    fields=[
        ("VLAN ID", str(mgmt["id"]), vlan_id),
        ("VLAN navn", mgmt["name"], not_empty),
        ("Netværk (A.B.C.D)", mgmt["net"], ipv4_addr),
        ("Prefix (CIDR)", str(mgmt["prefix"]), prefix_validator),
    ]
    out=text_input(stdscr,"MGMT – parametre", fields)
    if out is None: return None
    maxhosts = 2**(32-int(out["Prefix (CIDR)"]))
    offs = text_input(stdscr,"MGMT – GW/SVI offsets",[
        ("GW host (offset)", str(mgmt.get("gw_host",1)), host_octet_range(maxhosts)),
        ("SVI host (offset)",str(mgmt.get("svi_host",2)), host_octet_range(maxhosts)),
    ])
    if offs is None: return None
    return {
        "id": int(out["VLAN ID"]),
        "name": out["VLAN navn"],
        "net": out["Netværk (A.B.C.D)"],
        "prefix": int(out["Prefix (CIDR)"]),
        "gw_host": int(offs["GW host (offset)"]),
        "svi_host": int(offs["SVI host (offset)"]),
        "purpose": "mgmt"
    }

    # læg denne konstant et sted i toppen ved VLAN-editoren
PURPOSES = ["general", "access-default", "printer", "voice", "guest"]

def add_custom_vlan(stdscr):
    """
    Opret et nyt (custom) VLAN: navn, ID, net og prefix + purpose.
    Returnerer et dict med felterne eller None ved afbrudt.
    """
    fields = [
        ("Navn", "DATA", not_empty),
        ("VLAN ID", "20", vlan_id),
        ("Netværk (A.B.C.D)", "192.168.20.0", ipv4_addr),
        ("Prefix (CIDR)", "24", prefix_validator),
    ]
    out = text_input(stdscr, "Tilføj VLAN", fields)
    if out is None:
        return None

    pidx = menu(stdscr, "Purpose (brug)", PURPOSES, start_index=0)
    if pidx is None:
        return None

    return {
        "name": out["Navn"],
        "id": int(out["VLAN ID"]),
        "net": out["Netværk (A.B.C.D)"],
        "prefix": int(out["Prefix (CIDR)"]),
        "purpose": PURPOSES[pidx],
    }


def edit_custom_vlan(stdscr, key, vlan, existing_keys):
    # Felter med prefill
    fields = [
        ("Navn", vlan["name"], not_empty),
        ("VLAN ID", str(vlan["id"]), vlan_id),
        ("Netværk (A.B.C.D)", vlan["net"], ipv4_addr),
        ("Prefix (CIDR)", str(vlan["prefix"]), prefix_validator),
    ]
    out = text_input(stdscr, "Rediger VLAN", fields)
    if out is None:
        return None, None

    # Purpose-menu (prefill)
    try:
        start_idx = PURPOSES.index(vlan.get("purpose", "general"))
    except ValueError:
        start_idx = 0
    pidx = menu(stdscr, "Purpose (brug)", PURPOSES, start_index=start_idx)
    if pidx is None:
        return None, None

    new_val = {
        "name": out["Navn"],
        "id": int(out["VLAN ID"]),
        "net": out["Netværk (A.B.C.D)"],
        "prefix": int(out["Prefix (CIDR)"]),
        "purpose": PURPOSES[pidx],
    }

    # Evt. nyt key-navn hvis navn/ID ændres – undgå kollisioner
    base_key = slugify(f"{new_val['name']}-{new_val['id']}")
    new_key = base_key
    if new_key != key:
        i = 2
        while new_key in existing_keys and new_key != key:
            new_key = f"{base_key}-{i}"
            i += 1

    return new_key, new_val


def list_custom_vlans(vlans):
    return [(k,v) for k,v in vlans.items() if k!="mgmt"]

def make_profile(stdscr):
    # profilnavn
    res=text_input(stdscr,"Ny VLAN-profil (navn)",[("Profilnavn","office-custom",not_empty)])
    if res is None: return None
    name=res["Profilnavn"]

    # MGMT
    mgd=DEFAULT_PROFILE["vlans"]["mgmt"]
    mg=edit_mgmt(stdscr, mgd)
    if mg is None: return None

    # Custom VLAN list editor
    custom = {}
    while True:
        entries = list_custom_vlans({"mgmt": mg, **custom})  # [(key, vlan), ...] uden mgmt
        labels  = [f"{v['name']} (VLAN {v['id']}, {v.get('purpose','general')})" for _, v in entries]

        # Vælg eksisterende for at REDIGERE (hurtigvej), eller brug menuen
        choice = menu(
            stdscr,
            "Custom VLANs",
            labels + ["+ Tilføj", "↻ Rediger", "- Fjern", "Færdig"],
            start_index=len(labels)
        )
        if choice is None:
            return None

        if choice is not None and choice < len(labels):
            # Direkte EDIT på valgt VLAN
            k, v = entries[choice]
            new_key, new_val = edit_custom_vlan(stdscr, k, v, set(custom.keys()))
            if new_key and new_val:
                if new_key != k:
                    custom.pop(k, None)
                custom[new_key] = new_val
            continue

        # + Tilføj
        if choice == len(labels):
            nv = add_custom_vlan(stdscr)
            if nv:
                key = slugify(f"{nv['name']}-{nv['id']}")
                if key in custom:
                    i = 2
                    base = key
                    while key in custom:
                        key = f"{base}-{i}"
                        i += 1
                custom[key] = nv
            continue

        # ↻ Rediger (vælg først hvilket)
        if choice == len(labels) + 1:
            if not entries:
                _toast(stdscr, "Ingen at redigere"); continue
            eidx = menu(stdscr, "Rediger hvilket?", labels)
            if eidx is None: continue
            k, v = entries[eidx]
            new_key, new_val = edit_custom_vlan(stdscr, k, v, set(custom.keys()))
            if new_key and new_val:
                if new_key != k:
                    custom.pop(k, None)
                custom[new_key] = new_val
            continue

        # - Fjern
        if choice == len(labels) + 2:
            if not entries:
                _toast(stdscr, "Ingen at fjerne"); continue
            ridx = menu(stdscr, "Fjern hvilket?", labels)
            if ridx is None: continue
            k, _ = entries[ridx]
            custom.pop(k, None)
            continue

        # Færdig
        if choice == len(labels) + 3:
            break


    vlans={"mgmt": mg}
    vlans.update(custom)
    return {"name": name, "vlans": vlans}

# ==================== Profiles UI ====================
def pick_profile(stdscr, profiles):
    names=[p["name"] for p in profiles]
    idx=menu(stdscr,"Vælg VLAN-profil",names+["Tilbage"])
    if idx is None or idx==len(names): return None
    return profiles[idx]

def profiles_flow(stdscr, profiles):
    actions=["Vælg aktiv profil","Opret ny profil","Slet profil","Tilbage"]
    while True:
        a=menu(stdscr,"VLAN-profiler",actions)
        if a is None or a==3: return profiles
        if a==0:
            p=pick_profile(stdscr, profiles)
            if p: _toast(stdscr,f"Aktiv: {p['name']}")
        elif a==1:
            p=make_profile(stdscr)
            if p: profiles.append(p); save_profiles(profiles); _toast(stdscr,f"Tilføjet: {p['name']}")
        elif a==2:
            if not profiles: _toast(stdscr,"Ingen profiler"); continue
            p=pick_profile(stdscr, profiles)
            if p:
                profiles=[x for x in profiles if x["name"]!=p["name"]]
                save_profiles(profiles); _toast(stdscr,"Slettet")

# ==================== Port helpers ====================
def iface_name(prefix, n): return f"{prefix}{n}"
def make_range(prefix, start, end):
    return f"{prefix}{start}" if start==end else f"{prefix}{start} - {end}"
def join_ranges(ranges): return ", ".join(ranges)

def compute_port_groups(base_ports, base_prefix, extra_slots, extra_prefix, uplinks, printers,
                        base_start=1, extra_start=1):
    uplinks  = max(0, int(uplinks))
    printers = max(0, int(printers))
    extra_slots = max(0, int(extra_slots))

    # 1) Printer-porte = ALTID de sidste N i base
    prn = min(printers, base_ports)
    pr_first = base_start + base_ports - prn if prn > 0 else None

    # 2) Uplinks: brug ekstra slots først
    use_extra = min(uplinks, extra_slots)
    remain = uplinks - use_extra

    uplink_ranges = []
    if use_extra > 0:
        uplink_ranges.append(make_range(extra_prefix, extra_start, extra_start + use_extra - 1))

    # Hvis uplinks > extra_slots, tag resten fra TOPPEN af base (lige over printer-området)
    use_base = 0
    ul_base_start = ul_base_end = None
    if remain > 0:
        ul_base_end = (pr_first - 1) if pr_first else (base_start + base_ports - 1)
        use_base = max(0, min(remain, ul_base_end - base_start + 1))
        ul_base_start = ul_base_end - use_base + 1
        if use_base > 0:
            uplink_ranges.append(make_range(base_prefix, ul_base_start, ul_base_end))

    # 3) Access = resten af base (1 .. før uplink_base_start eller før printer)
    ac_end = (pr_first - 1) if pr_first else (base_start + base_ports - 1)
    if use_base > 0:
        ac_end = min(ac_end, ul_base_start - 1)

    access_ranges = []
    if ac_end is not None and ac_end >= base_start:
        access_ranges.append(make_range(base_prefix, base_start, ac_end))

    # 4) Printer-liste (enkeltvis)
    printer_list = []
    if prn > 0:
        end = base_start + base_ports - 1
        for p in range(pr_first, end + 1):
            printer_list.append(iface_name(base_prefix, p))

    return access_ranges, uplink_ranges, printer_list


# ==================== Features ====================
BASE_FEATURES = [
    ("STP hardening (bpduguard/default, portfast edge)", True),
    ("DHCP snooping + IP source guard", True),
    ("Port-security (sticky MAC på access-porte)", True),
    ("Storm-control (broadcast/multicast/unicast)", True),
    ("LLDP enable", True),
    ("Logging + NTP + timezone", False),
    ("SNMPv3 skabelon", False),
    ("Embed SSH public key", False),
]

# ==================== IFACE choices ====================
IFACE_CHOICES = [
    "FastEthernet0/",
    "GigabitEthernet0/",
    "GigabitEthernet1/0/",
    "TenGigabitEthernet1/1/",
    "Custom…",
]

def pick_prefix(stdscr, title, default):
    start = IFACE_CHOICES.index(default) if default in IFACE_CHOICES else 0
    idx=menu(stdscr, title, IFACE_CHOICES, start_index=start)
    if idx is None: return None
    choice=IFACE_CHOICES[idx]
    if choice=="Custom…":
        res=text_input(stdscr,"Custom interface prefix",[("Prefix", default, iface_prefix_ok)])
        if res is None: return None
        return res["Prefix"]
    return choice

# ==================== Switch VLAN selection ====================
def select_vlans_for_switch(stdscr, profile):
    # mgmt altid først og låst til ON
    keys=["mgmt"] + [k for k in profile["vlans"].keys() if k!="mgmt"]
    items=[]
    for k in keys:
        v=profile["vlans"][k]
        lbl=f"{v['name']} – VLAN {v['id']} ({v.get('purpose','general')})"
        default = True if k=="mgmt" else True  # default ON; sluk manuelt
        if k=="mgmt": lbl += " (obligatorisk)"
        items.append((lbl, default))
    sel=checkbox_menu(stdscr,"Vælg VLANs til denne switch", items)
    if sel is None: return None
    out={}
    i=0
    for k in keys:
        out[k] = True if k=="mgmt" else list(sel.values())[i]
        i+=1
    return out

# ==================== Config generator ====================
def gen_config(params, features, profile, chosen_vlans, access_default_vid=None):
    h=params["Hostname"]; model=params["Model"]
    base_ports={"16P":16,"24P":24,"48P":48}.get(model,24)

    base_prefix=params["Base iface prefix"]
    extra_prefix=params["Extra uplink prefix"]
    extra_slots=int(params["Extra uplink slots"])
    upl_count=int(params["Uplink count"])
    prn_count=int(params.get("Printer count","0"))

    pv=profile["vlans"]
    mg=pv["mgmt"]
    mg_pref=int(mg["prefix"])
    mg_net_int=ip_to_int(mg["net"])
    mg_mask=mask_from_prefix(mg_pref)

    maxhosts=2**(32-mg_pref)
    svi_host=max(1, min(maxhosts-1, int(params["Mgmt SVI host"])))
    gw_host =max(1, min(maxhosts-1, int(params["Mgmt GW host"])))
    mgmt_ip=int_to_ip(mg_net_int + svi_host)
    gw_ip  =int_to_ip(mg_net_int + gw_host)

    # port-grupper
    access_ranges, uplink_ranges, printer_list = compute_port_groups(
        base_ports, base_prefix, extra_slots, extra_prefix, upl_count, prn_count
    )

    # allowed på trunk = valgte VLANs
    allowed_ids=[v["id"] for k,v in pv.items() if chosen_vlans.get(k,False)]
    allowed_ids=sorted(set(allowed_ids))

    # find purpose VLANs blandt de valgte
    def find_purpose(purpose):
        for k,v in pv.items():
            if chosen_vlans.get(k,False) and v.get("purpose") == purpose:
                return v
        return None
    v_access = None
    if access_default_vid:
        v_access = {"id": int(access_default_vid)}
    else:
        v_access = find_purpose("access-default")

    v_printer = find_purpose("printer")
    v_voice   = find_purpose("voice")
    v_guest   = find_purpose("guest")

    now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    out=[]; emit=out.append
    emit("! ======================================================")
    emit(f"! Base skabelon genereret {now}")
    emit(f"! Model: {model} • Base: {base_ports} @ {base_prefix} • Extra uplinks: {extra_slots} @ {extra_prefix}")
    emit(f"! Uplinks valgt: {upl_count} • Printerporte: {prn_count}")
    emit(f"! Profil: {profile['name']} • VLANs medtaget: " + ",".join([pv[k]['name'] for k,b in chosen_vlans.items() if b]))
    emit("! ======================================================")
    emit(f"hostname {h}")
    emit("no ip domain-lookup")
    emit(f"ip domain-name {params['Domain']}")
    emit("service timestamps debug datetime msec")
    emit("service timestamps log datetime msec")
    emit("service password-encryption")
    emit("vtp mode transparent")
    emit("!")

    # VLAN-deklarationer
    for k,v in pv.items():
        if not chosen_vlans.get(k,False): continue
        emit(f"vlan {v['id']}"); emit(f" name {v['name']}"); emit("!")

    # MGMT SVI + GW
    emit(f"interface Vlan{mg['id']}")
    emit(" description *** Management SVI ***")
    emit(f" ip address {mgmt_ip} {mg_mask}")
    emit(" no shut"); emit("!")
    emit(f"ip default-gateway {gw_ip}"); emit("!")

    # SSH & lines
    emit("ip ssh version 2")
    emit(f"crypto key generate rsa modulus {params['SSH key bits']}")
    emit("ip scp server enable")
    emit("username admin privilege 15 secret 0 CHANGEME-StrongSecret")
    emit("enable secret 0 CHANGEME-Enable")
    emit("line con 0"); emit(" logging synchronous"); emit(" exec-timeout 10 0")
    emit("line vty 0 4"); emit(" transport input ssh"); emit(" exec-timeout 15 0"); emit(" login local"); emit("!")
    emit("banner login ^"); emit("  Uautoriseret adgang forbudt. Overvågning kan forekomme."); emit("^"); emit("!")

    # Optional services
    if features.get("Logging + NTP + timezone", False):
        emit("clock timezone CET 1 0")
        emit("clock summer-time CEST recurring last Sun Mar 2:00 last Sun Oct 3:00")
        if params.get("Syslog server"): emit(f"logging host {params['Syslog server']}")
        emit("logging buffered 16384"); emit("logging trap informational")
        if params.get("NTP server"): emit(f"ntp server {params['NTP server']}")
        emit("!")
    if features.get("LLDP enable", False): emit("lldp run"); emit("!")
    if features.get("STP hardening (bpduguard/default, portfast edge)", False):
        emit("spanning-tree mode pvst")
        emit("spanning-tree portfast default")
        emit("spanning-tree bpduguard default")
        emit("!")

    # DHCP snooping
    if features.get("DHCP snooping + IP source guard", False):
        vlan_list=[str(v["id"]) for k,v in pv.items() if chosen_vlans.get(k,False)]
        emit("ip dhcp snooping")
        emit("ip dhcp snooping verify mac-address")
        emit("ip dhcp snooping information option")
        if vlan_list: emit("ip dhcp snooping vlan " + ",".join(vlan_list))
        emit("!")

    # ACCESS-porte
    if access_ranges:
        emit(f"interface range {join_ranges(access_ranges)}")
        emit(" description *** ACCESS-PORTS ***")
        emit(" switchport mode access")
        if v_access:
            emit(f" switchport access vlan {v_access['id']}")
        emit(" spanning-tree portfast")
        emit(" spanning-tree bpduguard enable")
        if features.get("Storm-control (broadcast/multicast/unicast)", True):
            emit(" storm-control broadcast level 5.00")
            emit(" storm-control multicast level 5.00")
            emit(" storm-control unicast level 5.00")
            emit(" storm-control action shutdown")
        if features.get("Port-security (sticky MAC på access-porte)", True):
            emit(" switchport port-security")
            emit(" switchport port-security maximum 2")
            emit(" switchport port-security mac-address sticky")
            emit(" switchport port-security violation restrict")
        if features.get("DHCP snooping + IP source guard", False):
            emit(" ip verify source")
        emit(" no shut"); emit(" exit"); emit("!")

    # UPLINKS – trunk
    if uplink_ranges:
        emit(f"interface range {join_ranges(uplink_ranges)}")
        emit(" description *** UPLINK(S) ***")
        emit(" switchport mode trunk")
        if allowed_ids:
            emit(" switchport trunk allowed vlan " + ",".join(map(str,allowed_ids)))
        if features.get("DHCP snooping + IP source guard", False):
            emit(" ip dhcp snooping trust")
        emit(" spanning-tree link-type point-to-point")
        emit(" no shut"); emit(" exit"); emit("!")

    # PRINTER-porte
    if v_printer:
        for p in printer_list:
            emit(f"interface {p}")
            emit(" description *** PRINTER-PORT ***")
            emit(" switchport mode access")
            emit(f" switchport access vlan {v_printer['id']}")
            emit(" spanning-tree portfast")
            emit(" spanning-tree bpduguard enable")
            emit(" switchport port-security")
            emit(" switchport port-security maximum 1")
            emit(" switchport port-security mac-address sticky")
            emit(" switchport port-security violation restrict")
            emit(" no shut"); emit(" exit"); emit("!")

    # Hints for voice/guest
    if v_voice:
        emit(f"! Voice VLAN {v_voice['id']}: pr. port fx:")
        emit(f"!  interface {base_prefix}x")
        emit(f"!   switchport voice vlan {v_voice['id']}")
        emit("!")
    if v_guest:
        emit(f"! Guest VLAN {v_guest['id']}: brug efter behov på porte/SSID.")
        emit("!")

    # SNMPv3
    if features.get("SNMPv3 skabelon", False):
        emit("snmp-server group NETOPS v3 priv")
        emit("snmp-server user netops NETOPS v3 auth sha CHANGEME-Auth priv aes 128 CHANGEME-Priv")
        emit("snmp-server contact NetOps"); emit("snmp-server location CHANGE-ME"); emit("!")

    # SSH pubkey
    if features.get("Embed SSH public key", False) and params.get("SSH pub path"):
        try:
            with open(params["SSH pub path"], "r", encoding="utf-8") as f:
                pubkey=f.read().strip()
            emit("ip ssh pubkey-chain")
            emit(f" username {params.get('SSH username','admin')}")
            emit("  key-string"); emit(f"   {pubkey}")
            emit("  exit"); emit(" exit"); emit("!")
        except Exception as e:
            emit(f"! ADVARSEL: Kunne ikke læse pubkey: {e}"); emit("!")

    emit("do write memory"); emit("!")
    return "\n".join(out)

# ==================== Text flows ====================
PT_DEFAULTS = {
    "16P": {"base_prefix":"FastEthernet0/","extra_prefix":"GigabitEthernet0/","extra_slots":0},
    "24P": {"base_prefix":"FastEthernet0/","extra_prefix":"GigabitEthernet0/","extra_slots":2},  # PT 2960
    "48P": {"base_prefix":"FastEthernet0/","extra_prefix":"GigabitEthernet0/","extra_slots":2},
}

def pick_prefixes(stdscr, model):
    d=PT_DEFAULTS.get(model, {"base_prefix":"GigabitEthernet1/0/","extra_prefix":"GigabitEthernet1/0/","extra_slots":4})
    bp=pick_prefix(stdscr,"Vælg BASE interface-type", d["base_prefix"])
    if bp is None: return None
    ep=pick_prefix(stdscr,"Vælg UPLINK interface-type", d["extra_prefix"])
    if ep is None: return None
    return bp, ep, d["extra_slots"]

def text_form(stdscr, features, profile, model, bp, ep, extra_slots_default):
    mg=profile["vlans"]["mgmt"]
    maxhosts=2**(32-int(mg["prefix"]))
    fields=[
        ("Hostname","SW-ACCESS-01",not_empty),
        ("Mgmt SVI host", str(mg.get("svi_host",2)), host_octet_range(maxhosts)),
        ("Mgmt GW host",  str(mg.get("gw_host",1)), host_octet_range(maxhosts)),
        ("Domain","corp.local",not_empty),
        ("SSH key bits","2048", int_range(1024,4096)),
        ("Uplink count","2", int_range(0,32)),
        ("Extra uplink slots", str(extra_slots_default), int_range(0,32)),
    ]
    if features.get("Logging + NTP + timezone", False):
        a,b,c,_=map(int, mg["net"].split('.'))
        fields += [
            ("Syslog server", f"{a}.{b}.{c}.10", ipv4_addr),
            ("NTP server",    f"{a}.{b}.{c}.11", ipv4_addr),
        ]
    if features.get("Embed SSH public key", False):
        fields += [
            ("SSH username", "admin", not_empty),
            ("SSH pub path", os.path.expanduser("~/.ssh/id_rsa.pub"), not_empty),
        ]
    vals=text_input(stdscr,"Basis-parametre",fields)
    if vals is None: return None
    vals["Base iface prefix"]=bp
    vals["Extra uplink prefix"]=ep
    return vals

def choose_access_default_if_needed(stdscr, profile, chosen):
    # find inkluderede VLANs (ex MGMT) og scan for purpose access-default
    candidates=[]
    preset=None
    for k,v in profile["vlans"].items():
        if not chosen.get(k,False) or k=="mgmt": continue
        candidates.append((k,v))
        if v.get("purpose")=="access-default": preset=v["id"]
    if preset: return preset
    if not candidates: return None
    labels=[f"{v['name']} (VLAN {v['id']})" for _,v in candidates]
    idx=menu(stdscr,"Vælg default ACCESS-VLAN (eller q for ingen)", labels)
    if idx is None: return None
    return candidates[idx][1]["id"]

def new_file_flow(stdscr, profiles):
    models=["16P","24P","48P"]
    midx=menu(stdscr,"Vælg switch-model",models)
    if midx is None: return
    model=models[midx]

    prof=pick_profile(stdscr, profiles)
    if prof is None: return

    chosen=select_vlans_for_switch(stdscr, prof)
    if chosen is None: return

    features=checkbox_menu(stdscr,"Vælg features (flueben)", BASE_FEATURES)
    if features is None: return

    pp=pick_prefixes(stdscr, model)
    if pp is None: return
    bp,ep,extra_slots_default=pp

    vals=text_form(stdscr, features, prof, model, bp, ep, extra_slots_default)
    if vals is None: return
    vals["Model"]=model

    # printer count kun hvis et valgt VLAN har purpose=printer
    has_printer=False
    for k,v in prof["vlans"].items():
        if chosen.get(k,False) and v.get("purpose")=="printer":
            has_printer=True; break
    if has_printer:
        pc=text_input(stdscr,"Printer-porte (sidste N i base)",[("Printer count","1", int_range(0,16))])
        if pc is None: return
        vals["Printer count"]=pc["Printer count"]
    else:
        vals["Printer count"]="0"

    # access-default hvis nødvendigt
    access_vid = choose_access_default_if_needed(stdscr, prof, chosen)

    if not features.get("Logging + NTP + timezone", False):
        vals["Syslog server"]=""
        vals["NTP server"]=""

    cfg=gen_config(vals, features, prof, chosen, access_default_vid=access_vid)
    fname=f"{vals['Hostname']}-baseline.cfg"
    with open(fname,"w",encoding="utf-8") as f: f.write(cfg)
    _toast(stdscr,f"Skrevet: {fname}")
    show_preview(stdscr, cfg, title=f"{fname} (forhåndsvisning)")

# ==================== Main menu ====================
def main_menu(stdscr):
    curses.curs_set(0); stdscr.keypad(True)
    profiles=load_profiles()
    options=["Ny fil (generér boilerplate)","Åbn fil (ikke implementeret)","VLAN-profiler","Afslut"]
    while True:
        idx=menu(stdscr,"Cisco Config Skabelon",options)
        if idx is None or idx==3: break
        if idx==0: new_file_flow(stdscr, profiles)
        elif idx==1: _toast(stdscr,"Åbn fil er ikke implementeret endnu")
        elif idx==2: profiles=profiles_flow(stdscr, profiles)

def main(): curses.wrapper(main_menu)
if __name__ == "__main__": main()
