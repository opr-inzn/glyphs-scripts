# MenuTitle: Add unicodeRange and codePageRange
# -*- coding: utf-8 -*-

"""
Compares font coverage vs. OS/2 Unicode Ranges & Code Page Ranges.
"""

from GlyphsApp import Glyphs, GSCustomParameter

# ---------- settings ----------
UNICODE_THRESHOLD = 4.0
CODEPAGE_THRESHOLD = 60.0
MERGE_EXISTING = False  # set True to merge with previously set bits instead of overwriting

# ---------- helpers ----------
def show_panel():
    try:
        Glyphs.clearLog()
    except Exception:
        pass
    try:
        Glyphs.showMacroWindow()
    except Exception:
        pass

font = Glyphs.font
if not font:
    raise Exception("No font open.")

# Collect encoded codepoints
codepoints = set()
for g in font.glyphs:
    uc = g.unicode
    if uc:
        try:
            codepoints.add(int(uc, 16))
        except Exception:
            pass

if not codepoints:
    show_panel()
    print("No encoded glyphs found in this font.")
    raise SystemExit

# ---------- Unicode Ranges (OS/2 ulUnicodeRange* bit → (label, start, end)) ----------
# Based on Microsoft OpenType OS/2 table spec (v1.9.1). (List condensed to the ranges most relevant in general desktop fonts;
# you can extend freely by adding more bits from the spec with their ranges.)
UNICODE_RANGES = {
    0:  ("Basic Latin", 0x0000, 0x007F),
    1:  ("Latin-1 Supplement", 0x0080, 0x00FF),
    2:  ("Latin Extended-A", 0x0100, 0x017F),
    3:  ("Latin Extended-B", 0x0180, 0x024F),
    4:  ("IPA Extensions", 0x0250, 0x02AF),
    5:  ("Spacing Modifier Letters", 0x02B0, 0x02FF),
    6:  ("Combining Diacritical Marks", 0x0300, 0x036F),
    7:  ("Greek and Coptic", 0x0370, 0x03FF),
    9:  ("Cyrillic", 0x0400, 0x04FF),
    10: ("Armenian", 0x0530, 0x058F),
    11: ("Hebrew", 0x0590, 0x05FF),
    13: ("Arabic", 0x0600, 0x06FF),
    15: ("Devanagari", 0x0900, 0x097F),
    16: ("Bengali", 0x0980, 0x09FF),
    17: ("Gurmukhi", 0x0A00, 0x0A7F),
    18: ("Gujarati", 0x0A80, 0x0AFF),
    19: ("Oriya", 0x0B00, 0x0B7F),
    20: ("Tamil", 0x0B80, 0x0BFF),
    21: ("Telugu", 0x0C00, 0x0C7F),
    22: ("Kannada", 0x0C80, 0x0CFF),
    23: ("Malayalam", 0x0D00, 0x0D7F),
    24: ("Thai", 0x0E00, 0x0E7F),
    25: ("Lao", 0x0E80, 0x0EFF),
    26: ("Georgian", 0x10A0, 0x10FF),
    28: ("Hangul Jamo", 0x1100, 0x11FF),
    29: ("Latin Extended Additional", 0x1E00, 0x1EFF),
    30: ("Greek Extended", 0x1F00, 0x1FFF),
    31: ("General Punctuation", 0x2000, 0x206F),
    32: ("Superscripts and Subscripts", 0x2070, 0x209F),
    33: ("Currency Symbols", 0x20A0, 0x20CF),
    34: ("Combining Diacritical Marks for Symbols", 0x20D0, 0x20FF),
    35: ("Letterlike Symbols", 0x2100, 0x214F),
    36: ("Number Forms", 0x2150, 0x218F),
    37: ("Arrows", 0x2190, 0x21FF),
    38: ("Mathematical Operators", 0x2200, 0x22FF),
    39: ("Miscellaneous Technical", 0x2300, 0x23FF),
    40: ("Control Pictures", 0x2400, 0x243F),
    41: ("Optical Character Recognition", 0x2440, 0x245F),
    42: ("Enclosed Alphanumerics", 0x2460, 0x24FF),
    43: ("Box Drawing", 0x2500, 0x257F),
    44: ("Block Elements", 0x2580, 0x259F),
    45: ("Geometric Shapes", 0x25A0, 0x25FF),
    46: ("Miscellaneous Symbols", 0x2600, 0x26FF),
    47: ("Dingbats", 0x2700, 0x27BF),
    48: ("CJK Symbols and Punctuation", 0x3000, 0x303F),
    49: ("Hiragana", 0x3040, 0x309F),
    50: ("Katakana", 0x30A0, 0x30FF),
    51: ("Bopomofo", 0x3100, 0x312F),
    52: ("Hangul Compatibility Jamo", 0x3130, 0x318F),
    56: ("Hangul Syllables", 0xAC00, 0xD7AF),
    57: ("Non-Plane 0", 0x10000, 0x10FFFF),
    59: ("CJK Unified Ideographs", 0x4E00, 0x9FFF),
    60: ("Private Use Area (plane 0)", 0xE000, 0xF8FF),
    61: ("CJK Strokes", 0x31C0, 0x31EF),
    62: ("Alphabetic Presentation Forms", 0xFB00, 0xFB4F),
    63: ("Arabic Presentation Forms-A", 0xFB50, 0xFDFF),
    64: ("Combining Half Marks", 0xFE20, 0xFE2F),
    65: ("CJK Compatibility Forms", 0xFE30, 0xFE4F),
    66: ("Small Form Variants", 0xFE50, 0xFE6F),
    67: ("Arabic Presentation Forms-B", 0xFE70, 0xFEFF),
    68: ("Halfwidth And Fullwidth Forms", 0xFF00, 0xFFEF),
    69: ("Specials", 0xFFF0, 0xFFFF),
}

# ---------- Code Page Ranges (exact per spec) ----------
# Bit → ("label", [sample Unicode points to test])
# Notes:
# - Bits 9–15, 22–28, 32–47 are Reserved in the spec and intentionally omitted.
# - Bit 30 (OEM Character Set) & 31 (Symbol) are not auto-set here.
CODEPAGES = {
    0:  ("1252 Latin 1 (Western Europe)",        [0x0041,0x0061,0x00C9,0x00E9,0x00F6,0x00FC,0x00E0,0x00E7]),
    1:  ("1250 Latin 2 (Eastern Europe)",        [0x0104,0x010C,0x0118,0x0141,0x015A,0x0160,0x0179]),
    2:  ("1251 Cyrillic",                        [0x0410,0x042F,0x0430,0x044F]),
    3:  ("1253 Greek",                           [0x0391,0x03A9,0x03B1,0x03C9]),
    4:  ("1254 Turkish",                         [0x011E,0x0130,0x015E,0x00E7,0x00FC]),
    5:  ("1255 Hebrew",                          [0x05D0,0x05EA]),
    6:  ("1256 Arabic",                          [0x0627,0x0644,0x0645]),
    7:  ("1257 Windows Baltic",                  [0x0104,0x0160,0x017E,0x017B]),
    8:  ("1258 Vietnamese",                      [0x1EA0,0x1EF9]),
    16: ("874 Thai",                              [0x0E01,0x0E40,0x0E44]),
    17: ("932 JIS/Japan",                         [0x3042,0x30A2,0x4E00]),
    18: ("936 Chinese Simplified",                [0x4E00,0x4E8C,0x4E09]),
    19: ("949 Korean Wansung",                    [0xAC00,0xB098,0xC548]),
    20: ("950 Chinese Traditional",               [0x4E00,0x56DB,0x571F]),
    21: ("1361 Korean Johab",                     [0x1100,0x1161]),
    29: ("Macintosh Character Set (US Roman)",    [0x0041,0x0061,0x00C9,0x00E9,0x00F1,0x00F6,0x00FC,0x2019]),
    # 30 OEM Character Set  (not inferred)
    # 31 Symbol Character Set (not inferred)
    48: ("869 IBM Greek",                         [0x0386,0x0388,0x03A6,0x03C6]),
    49: ("866 MS-DOS Russian",                    [0x0410,0x042F,0x0430,0x044F]),
    50: ("865 MS-DOS Nordic",                     [0x00C5,0x00E5,0x00C6,0x00E6,0x00D8,0x00F8]),
    51: ("864 Arabic (DOS)",                      [0x0627,0x0644,0x0645]),
    52: ("863 MS-DOS Canadian French",            [0x00C9,0x00E9,0x00E8,0x00EA,0x00E7,0x00F9,0x00FB]),
    53: ("862 MS-DOS Hebrew",                     [0x05D0,0x05EA]),
    54: ("861 MS-DOS Icelandic",                  [0x00C6,0x00E6,0x00D0,0x00F0,0x00DE,0x00FE]),
    55: ("860 MS-DOS Portuguese",                 [0x00C0,0x00C3,0x00E3,0x00E9,0x00EA,0x00E7]),
    56: ("857 IBM Turkish (DOS)",                 [0x011E,0x0130,0x015E,0x00E7,0x00FC]),
    57: ("855 IBM Cyrillic (DOS)",                [0x0410,0x042F,0x0430,0x044F]),
    58: ("852 Latin 2 (DOS Central Europe)",      [0x0104,0x010C,0x011A,0x0141,0x015A,0x0160,0x0179]),
    59: ("775 MS-DOS Baltic",                     [0x0104,0x0106,0x010C,0x0160,0x0179,0x017D]),
    60: ("737 Greek (DOS)",                       [0x0391,0x03A9,0x03B1,0x03C9]),
    61: ("708 Arabic (ASMO 708)",                 [0x0627,0x0644,0x0645]),
    62: ("850 WE / Latin 1 (DOS Western)",        [0x0041,0x0061,0x00C9,0x00E9,0x00F6,0x00FC,0x00E0,0x00E7]),
    63: ("437 US (MS-DOS)",                       [0x0041,0x0061,0x00C9,0x00E9,0x00F1,0x00F6,0x00FC]),
}

# ---------- coverage functions ----------
def unicode_coverage(codepoints, ranges):
    out = []
    for bit, (name, a, b) in ranges.items():
        cnt = sum(1 for cp in codepoints if a <= cp <= b)
        total = (b - a + 1)
        pct = (cnt / total) * 100.0 if cnt else 0.0
        out.append((bit, name, pct))
    return out

def codepage_coverage(codepoints, pages):
    out = []
    for bit, (name, required) in pages.items():
        if not required:
            out.append((bit, name, 0.0))
            continue
        miss = [cp for cp in required if cp not in codepoints]
        pct = (1.0 - len(miss) / float(len(required))) * 100.0
        out.append((bit, name, pct))
    return out

# ---------- compute ----------
uni_results = unicode_coverage(codepoints, UNICODE_RANGES)
cp_results  = codepage_coverage(codepoints, CODEPAGES)

uni_bits = [bit for bit, _, pct in uni_results if pct >= UNICODE_THRESHOLD]
cp_bits  = [bit for bit, _, pct in cp_results  if pct >= CODEPAGE_THRESHOLD]

def codepage_id_for_bit(bit):
    """Return Glyphs-compatible token for codePageRanges."""
    if bit == 29:
        return "bit 29"  # Macintosh Character Set (US Roman)
    label = CODEPAGES[bit][0]
    first = label.split()[0]
    return first if first.isdigit() else label

cp_values = [codepage_id_for_bit(b) for b in cp_bits]

# ---------- merge with existing ----------
if MERGE_EXISTING:
    try:
        prev_uni = list(font.customParameters.get("unicodeRanges") or [])
        prev_cp  = list(font.customParameters.get("codePageRanges") or [])
    except Exception:
        prev_uni, prev_cp = [], []
    prev_uni_clean = [int(str(u).lstrip("!")) for u in prev_uni]
    prev_cp_clean  = [str(v).lstrip("!") for v in prev_cp]
    uni_bits = sorted(set(prev_uni_clean) | set(uni_bits))
    cp_values = sorted(set(prev_cp_clean) | set(cp_values))

# ---------- ensure active GSCustomParameters ----------
def ensure_active_param(name, value):
    """Create or update a GSCustomParameter and ensure it’s active."""
    existing = None
    for cp in font.customParameters:
        if cp.name == name:
            existing = cp
            break

    if existing:
        existing.value = value
        existing.active = True
        print(f"🔓 Enabled existing {name} parameter.")
    else:
        new_param = GSCustomParameter()
        new_param.name = name
        new_param.value = value
        new_param.active = True
        font.customParameters.append(new_param)
        print(f"🆕 Added and enabled {name} parameter.")

# ---------- write parameters ----------
ensure_active_param("unicodeRanges", uni_bits)
ensure_active_param("codePageRanges", cp_values)

# ---------- report ----------
print("=== Unicode Ranges (OS/2 ulUnicodeRange*) ===")
for bit, name, pct in sorted(uni_results, key=lambda t: t[0]):
    mark = "✅" if bit in uni_bits else " "
    print(f"{bit:3d} {name:42s} : {pct:6.1f}% {mark}")

print("\n=== Code Page Ranges (OS/2 ulCodePageRange*) ===")
for bit, name, pct in sorted(cp_results, key=lambda t: t[0]):
    mark = "✅" if bit in cp_bits else " "
    print(f"{bit:3d} {name:42s} : {pct:6.1f}% {mark}")

print("\nUpdated custom parameters:")
print("  unicodeRanges  =", uni_bits)
print("  codePageRanges =", cp_bits)
print("\nDone.")
