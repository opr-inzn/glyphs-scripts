# MenuTitle: Set Export Folders for Instances
# -*- coding: utf-8 -*-
__doc__ = """
Sets the Export Folder for all instances based on the current family name.
Only the official Glyphs variable instance is treated as “Variable”.
“Unlicensed” instances get their own folder.
"""

from GlyphsApp import INSTANCETYPEVARIABLE
import unicodedata
import re

font = Glyphs.font
if not font:
    print("No font open.")
    raise SystemExit


# ---------- helpers ----------

def sanitize_name(s, for_folder=False, keep_spaces=False):
    if not s:
        return ""

    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("_", "-").replace("'", "")
    s = re.sub(r"[^A-Za-z0-9\s-]+", "-", s)
    s = s.strip()
    s = re.sub(r"\s+", " " if (for_folder or keep_spaces) else "-", s)
    s = re.sub(r"-+", "-", s).strip("-").strip()
    return s


def get_localized_family(instance):
    fam = None

    # 1) Look inside `properties` for localized familyNames
    if instance.properties:
        for prop in instance.properties:
            if prop.key == "familyNames" and prop.defaultValue:
                fam = prop.defaultValue
                break

    # 2) Check custom parameter "familyName"
    if not fam:
        if "familyName" in instance.customParameters:
            fam = instance.customParameters["familyName"]

    # 3) Fallback to global font family
    return fam or font.familyName or ""


def is_trial_instance(instance):
    fam = get_localized_family(instance)
    return bool(re.search(r"unlicensed\s*", fam, re.IGNORECASE))


def is_variable_instance(instance):
    # Option A: only the real Glyphs variable instance is variable
    return instance.type == INSTANCETYPEVARIABLE


# ---------- main ----------

updated = 0
base_family = sanitize_name(font.familyName, keep_spaces=True)

for instance in font.instances:
    trial = is_trial_instance(instance)
    var = is_variable_instance(instance)

    if trial and var:
        folder_name = f"{base_family} Unlicensed Variable"
    elif trial:
        folder_name = f"{base_family} Unlicensed"
    elif var:
        folder_name = f"{base_family} Variable"
    else:
        folder_name = base_family

    instance.customParameters["Export Folder"] = sanitize_name(folder_name, for_folder=True)
    updated += 1

print(f"✅ Updated Export Folder for {updated} instances.")
