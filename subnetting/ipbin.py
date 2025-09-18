#!/usr/bin/env python3
# ipbin.py - smart base/IPv4 converter (auto-detektion)
import sys
import re

HEX_RE = re.compile(r'^[0-9a-fA-F]+$')
BIN_RE = re.compile(r'^[01]+$')
DEC_RE = re.compile(r'^[0-9]+$')

def detect_base_token(tok: str):
    t = tok.strip()
    if t.lower().startswith('0x'):
        return 16, t[2:]
    if t.lower().startswith('0b'):
        return 2, t[2:]
    if re.search(r'[a-fA-F]', t):
        return 16, t
    if BIN_RE.fullmatch(t) and len(t) >= 2:
        return 2, t
    if DEC_RE.fullmatch(t):
        return 10, t
    if HEX_RE.fullmatch(t):
        return 16, t
    return 10, t

def parse_single(s: str):
    s_clean = s.replace('_','').strip()
    base, token = detect_base_token(s_clean)
    try:
        val = int(token, base)
    except ValueError:
        # fallback: try decimal
        val = int(token, 10)
        base = 10
    return val, base

def parse_dotted(s: str):
    parts = s.split('.')
    octets = []
    bases = []
    for p in parts:
        p_clean = p.replace('_','').strip()
        # dotted IPv4 notation is most commonly decimal. If the token is
        # composed of decimal digits we optimistically parse it as such and
        # only fall back to the auto-detected base when the decimal value is
        # outside the 0-255 range. This avoids interpreting typical inputs
        # like ``10`` as the binary value 2.
        if DEC_RE.fullmatch(p_clean):
            v_dec = int(p_clean, 10)
            if 0 <= v_dec <= 255:
                octets.append(v_dec)
                bases.append(10)
                continue
        base, tok = detect_base_token(p_clean)
        try:
            v = int(tok, base)
        except ValueError:
            v = int(tok, 10)
            base = 10
        if not (0 <= v <= 255):
            raise ValueError(f"Octet '{p}' -> {v} outside 0-255")
        octets.append(v)
        bases.append(base)
    return octets, bases

def int_to_hex(n: int, prefix=True, width_bits=None):
    if width_bits:
        hex_width = (width_bits + 3)//4
        h = format(n, 'x').zfill(hex_width)
    else:
        h = format(n, 'x')
    return ('0x' + h) if prefix else h

def int_to_bin(n: int, prefix=True, width_bits=None, group8=False):
    if width_bits:
        b = format(n, 'b').zfill(width_bits)
    else:
        b = format(n, 'b')
    if group8 and width_bits:
        # split into 8-bit groups (dotted)
        parts = [b[i:i+8] for i in range(0, len(b), 8)]
        s = '.'.join(parts)
        return ('0b' + s) if prefix else s
    return ('0b' + b) if prefix else b

def print_single(val: int):
    bitlen = val.bit_length() or 1
    byte_width = ((bitlen + 7)//8)*8
    print(f"DEC: {val}")
    print(f"HEX: {int_to_hex(val, prefix=True)}")
    print(f"BIN: {int_to_bin(val, prefix=True)}")
    print(f"HEX (padded to bytes): {int_to_hex(val, prefix=False, width_bits=byte_width)}")
    print(f"BIN (padded to bytes): {int_to_bin(val, prefix=False, width_bits=byte_width)}")

def print_dotted(octets, original_had_dots=True):
    dotted_dec = '.'.join(str(o) for o in octets)
    dotted_hex = '.'.join(format(o, '02x') for o in octets)
    dotted_bin = '.'.join(format(o, '08b') for o in octets)
    flat_int = 0
    for o in octets:
        flat_int = (flat_int << 8) | o
    print("=== Tolket som IPv4 octetter ===")
    print("DEC (dotted):", dotted_dec)
    print("HEX (dotted):", dotted_hex)
    print("BIN (dotted):", dotted_bin)
    print("--- Flat repr ---")
    print("DEC:", flat_int)
    print("HEX:", int_to_hex(flat_int, prefix=True, width_bits=32))
    print("BIN:", int_to_bin(flat_int, prefix=True, width_bits=32))

def main():
    if len(sys.argv) != 2:
        print("Usage: python ipbin.py <value>")
        print("Eksempler: 192.168.1.10   c0.a8.01.0a   0x1f   1101_1111")
        sys.exit(1)
    s = sys.argv[1].strip()
    if '/' in s:
        s = s.split('/',1)[0]

    try:
        if '.' in s:
            # dotted input (each part kan være hex/bin/dec)
            octets, bases = parse_dotted(s)
            print_dotted(octets, original_had_dots=True)
        else:
            val, detected_base = parse_single(s)
            # hvis input er entydigt 32-bit bin eller hex8, vis også ip
            s_nounder = s.replace('_','')
            show_ip = False
            if detected_base == 2 and len(s_nounder) == 32:
                show_ip = True
            if detected_base == 16 and len(s_nounder) == 8:
                show_ip = True
            if show_ip and 0 <= val <= 0xFFFFFFFF:
                octs = [(val >> 24)&0xff, (val >> 16)&0xff, (val >> 8)&0xff, val & 0xff]
                print_dotted(octs, original_had_dots=False)
            print_single(val)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
