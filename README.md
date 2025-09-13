# confdesign

## Oversigt
Dette repo samler små værktøjer, som jeg bygger under min IT-supporter-uddannelse.

## Værktøjer

Filerne `getconf.py`, `ipbin.py` og `newconfdesign.py` ligger i undermappen `intermediate/`.

### `Setconf.py`
Uploader konfiguration til et Cisco IOS-device via NAPALM med enten *merge* eller *replace*-mode.

Eksempel:
```bash
python Setconf.py --ssh 192.0.2.1 -u brugernavn -f config.txt --mode merge
```

### `intermediate/getconf.py`
Henter startup- og evt. running-config fra et device via SSH eller seriel COM og gemmer til fil.

Eksempel via SSH:
```bash
python intermediate/getconf.py --ssh 192.0.2.1 -u brugernavn -f backup.txt
```

Eksempel via COM:
```bash
python intermediate/getconf.py --com COM3 -f backup.txt
```

### `intermediate/ipbin.py`
Konverterer tal mellem decimal, hex og binær – og kan også tolke IPv4-adresser.

Eksempel:
```bash
python intermediate/ipbin.py 192.168.0.1
python intermediate/ipbin.py 0xff
```

### `intermediate/newconfdesign.py`
Tekstbaseret brugerflade (TUI) til at generere Cisco-switchkonfigurationer ud fra VLAN-profiler.  Kræver `curses` (på Windows: `pip install windows-curses`).

Eksempel:
```bash
python intermediate/newconfdesign.py
```

## Tak
Jeg har fået hjælp af min gode ven ChatGPT.
