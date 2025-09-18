# netops-toolkit

Et lille bibliotek af netværksværktøjer, som er blevet til under min IT-supporter-uddannelse.
Skripterne hjælper med daglig drift af Cisco-udstyr, subnet-beregninger og et par studiehjælpere.

## Installation

Alle værktøjer kører på Python 3.10+.
Opret gerne et virtuelt miljø og installer afhængighederne fra `requirements.txt`:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> `windows-curses` er kun nødvendigt på Windows, hvis `newconfdesign.py` skal bruges.

## Hurtigt overblik

| Kategori | Fil | Kort beskrivelse |
| --- | --- | --- |
| Device-automation | `Setconf.py` | Uploader konfiguration til Cisco IOS via NAPALM i merge/replace-mode. |
| Device-backup | `intermediate/getconf.py` | Henter startup- (og evt. running-) config via SSH eller seriel COM. |
| Config-design | `intermediate/newconfdesign.py` | Curses-baseret TUI til at bygge switch-profiler og generere konfiguration. |
| Subnetting | `subnetting/ipbin.py` | Konverter tal mellem decimal/hex/binær og tolker IPv4-adresser. |
| Subnetting | `subnetting/subnetcalc.py` | Beregner subnets, VLSM og eksport til CSV. |

## Værktøjerne i detaljer

### Setconf.py
Uploader en lokal konfigurationsfil til et Cisco IOS-device med NAPALM.
Viser et diff-panel via Rich før commit og kan automatisk rulle tilbage ved fejl.

```bash
python Setconf.py --ssh 192.0.2.1 -u brugernavn -f config.txt --mode merge
```

Flag:
- `--mode {merge,replace}` vælger merge- eller replace-mode.
- `--yes` skipper bekræftelses-prompt.
- `--rollback` udfører `rollback()` hvis commit fejler.

### intermediate/getconf.py
Tager backup af konfigurationen enten over SSH eller via seriel COM.

a) SSH (NAPALM):
```bash
python intermediate/getconf.py --ssh 192.0.2.1 -u brugernavn -f backups/router1.txt -c
```
`-c` gemmer også running-config.

b) Seriel COM:
```bash
python intermediate/getconf.py --com COM3 -f backups/router1.txt --baud 9600 -c
```
Programmet spørger efter passwords, hvis de ikke angives med flag.

### intermediate/newconfdesign.py
TUI der guider dig gennem oprettelse af VLAN-profiler og genererer et konfigurationsudkast.
Profiler gemmes i `profiles.json`, så de kan genbruges.

```bash
python intermediate/newconfdesign.py
```

### subnetting/ipbin.py
Smart base-konverter: forstår decimal, hex, binær og dotted IPv4. Viser både flade tal og oktetter.

```bash
python subnetting/ipbin.py 192.168.0.1
python subnetting/ipbin.py 0xff
python subnetting/ipbin.py 11000000101010000000000000000001
```

### subnetting/subnetcalc.py
Subnet-lommeregner der kan arbejde med både faste prefix og VLSM.

```bash
python subnetting/subnetcalc.py --base 192.168.100.0/24 --target-prefix 26
python subnetting/subnetcalc.py --base 10.0.0.0/24 --min-hosts 50
python subnetting/subnetcalc.py --base 192.168.10.0/24 --vlsm --csv subnets.csv
```

## Fremtidige tanker

Repoet har tidligere heddet `confdesign`.
Gamle placeholders som `ansible-confs/` og `todo` er fjernet for at holde fokus på de aktive værktøjer.
Hvis repoet omdøbes til `netops-toolkit` på GitHub matcher navnet nu projektets bredere fokus.
