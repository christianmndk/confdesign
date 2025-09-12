# confdesign

## Oversigt
Dette repo samler små værktøjer, som jeg bygger under min IT-supporter-uddannelse.

## Værktøjer

### `Setconf.py`
Uploader konfiguration til et Cisco IOS-device via NAPALM med enten *merge* eller *replace*-mode.

Eksempel:
```bash
python Setconf.py --ssh 192.0.2.1 -u brugernavn -f config.txt --mode merge
```

### `getconf.py`
Henter startup- og evt. running-config fra et device via SSH eller seriel COM og gemmer til fil.

Eksempel via SSH:
```bash
python getconf.py --ssh 192.0.2.1 -u brugernavn -f backup.txt
```

Eksempel via COM:
```bash
python getconf.py --com COM3 -f backup.txt
```

### `ipbin.py`
Konverterer tal mellem decimal, hex og binær – og kan også tolke IPv4-adresser.

Eksempel:
```bash
python ipbin.py 192.168.0.1
python ipbin.py 0xff
```

## Tak
Jeg har fået hjælp af min gode ven ChatGPT.
