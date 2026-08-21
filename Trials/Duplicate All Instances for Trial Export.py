# MenuTitle: Duplicate All Instances for Trial Export (Hide in Preview)
# -*- coding: utf-8 -*-
__doc__ = """
Duplicates all non-variable instances as “Unlicensed” versions.
After duplication, hides all trial instances from the preview window (👁)
but keeps them active for export.
"""

from GlyphsApp import Glyphs, INSTANCETYPEVARIABLE
import unicodedata
import re

font = Glyphs.font
if not font:
    print("No font open.")
    raise SystemExit

# ---------- helpers ----------

def sanitize_name(s, for_folder=False, keep_spaces=False):
    """Normalize and clean a string for safe filenames, PostScript names, or folder paths."""
    if not s:
        return ""

    # normalize accents, quotes etc.
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))  # remove accents

    # replace typographic quotes/apostrophes and underscores
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("_", "-").replace("'", "")  # remove apostrophes entirely

    # replace non-alphanumeric symbols with hyphens
    s = re.sub(r"[^A-Za-z0-9\s-]+", "-", s)

    # normalize spaces/hyphens
    s = s.strip()
    s = re.sub(r"\s+", " " if (for_folder or keep_spaces) else "-", s)
    s = re.sub(r"-+", "-", s).strip("-").strip()

    return s


def normalize_name(s):
    """Simplify a string for consistent comparison (accents removed, lowercase, single spaces)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s.strip().lower())
    return s


def get_family_name(inst):
    """Return best possible family name string for an instance."""
    fam = None
    try:
        fam = inst.customParameters["familyName"]
    except Exception:
        pass
    if not fam:
        fam = getattr(inst, "familyName", None)
    return fam or ""


def is_trial_instance(inst):
    """Return True if this instance is a trial version."""
    fam = get_family_name(inst)
    return "unlicensed" in fam.lower() if fam else False


def clean_family_name(name):
    """Remove trailing spaces, dashes, underscores, or dots from a family name and sanitize it."""
    if not name:
        return ""
    name = sanitize_name(name, keep_spaces=True)
    name = re.sub(r"[\s\-._]+$", "", name)
    return name.strip()


def get_effective_family_name(inst):
    """Return whichever family name Glyphs actually uses (localized or default)."""
    fam = None
    try:
        fam = inst.customParameters["familyName"]
    except Exception:
        pass
    if not fam:
        try:
            fam = inst.propertyForKey_languageTag_("familyNames", None)
        except Exception:
            pass
    if not fam:
        fam = getattr(inst, "familyName", "")
    return fam or ""


# ---------- duplication ----------

created_count = 0

try:
    originals = [i for i in font.instances if not is_trial_instance(i) and i.type != INSTANCETYPEVARIABLE]
except Exception:
    originals = [i for i in font.instances if not is_trial_instance(i)]

for instance in originals:
    base_family = get_effective_family_name(instance) or font.familyName
    base_family = clean_family_name(base_family)
    trial_family = f"{base_family} Unlicensed"
    style_name = instance.name or ""
    full_name = f"{trial_family} {style_name}".strip()

    # ✅ check if trial already exists
    duplicate_found = any(
        normalize_name(get_effective_family_name(i)) == normalize_name(trial_family)
        and normalize_name(i.name) == normalize_name(style_name)
        for i in font.instances
    )
    if duplicate_found:
        continue

    new_instance = instance.copy()
    new_instance.setProperty_value_languageTag_("familyNames", trial_family, None)
    new_instance.setProperty_value_languageTag_("postscriptFullNames", full_name, None)

    # consistent filename + export folder
    font_name = sanitize_name(full_name)
    new_instance.fontName = font_name
    new_instance.customParameters["Export Folder"] = sanitize_name(trial_family, for_folder=True)

    font.instances.append(new_instance)
    created_count += 1


# ---------- hide trials from preview ----------

hidden_count = 0
for inst in font.instances:
    fam = get_family_name(inst)
    if isinstance(fam, str) and "unlicensed" in fam.lower():
        try:
            inst.visible = False   # hide from 👁 preview
            hidden_count += 1
        except Exception as e:
            print(f"⚠️ Could not hide {inst.name}: {e}")

# ---------- summary ----------

if created_count:
    print(f"✅ Created {created_count} new 'Unlicensed' instance(s).")
else:
    print("⚠️ All trial instances already exist — nothing to duplicate.")

print(f"👁 Hidden {hidden_count} 'Unlicensed' instance(s) from preview.")
Glyphs.showNotification(
    "Duplicate + Hide Trials",
    f"Created {created_count}, hidden {hidden_count} 'Unlicensed' instances."
)