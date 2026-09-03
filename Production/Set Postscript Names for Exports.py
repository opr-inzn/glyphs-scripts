# MenuTitle: Set Postscript Names for Exports
# -*- coding: utf-8 -*-
__doc__ = """
Updates localized family/style names, PostScript names, fileNames, and Export
Folders for all instances. Instances named “Mono” keep that source style name,
receive “Regular” as their localized style name, use a Mono family suffix, and
share the base family’s Export Folder.
The PostScript FontName is kept identical to the export fileName.
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

    # remove LABxx only when NOT used for folder names
    if not for_folder:
        s = re.sub(r"(?i)\bLAB\d{1,3}\b", "", s)

    # normalize accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))

    # replace quotes/underscores
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("_", "-").replace("'", "")

    # non-alphanumeric → hyphen
    s = re.sub(r"[^A-Za-z0-9\s-]+", "-", s)

    # spacing rules
    s = s.strip()
    s = re.sub(r"\s+", " " if (for_folder or keep_spaces) else "-", s)
    s = re.sub(r"-+", "-", s).strip("-").strip()

    # final cleanup (avoid double spaces)
    s = re.sub(r"\s{2,}", " ", s)

    return s


def get_localized_family(instance):
    """Return localized or fallback family name safely."""
    fam = None
    try:
        fam = instance.propertyForKey_languageTag_("familyNames", None)
    except Exception:
        pass
    if instance.properties:
        for prop in instance.properties:
            if prop.key != "familyNames":
                continue
            prop_value = getattr(prop, "value", None) or getattr(prop, "defaultValue", None)
            if not fam and prop_value:
                fam = prop_value
                break
    if not fam:
        try:
            fam = instance.customParameters["familyName"]
        except Exception:
            pass
    return fam or font.familyName or ""


def is_trial_instance(instance):
    fam = get_localized_family(instance)
    return bool(re.search(r"unlicensed\s*", fam, re.IGNORECASE))


def is_variable_instance(instance):
    fam = get_localized_family(instance)
    return bool(re.search(r"\bvariable\b", fam, re.IGNORECASE))


def is_mono_instance(instance):
    """Recognise fresh Mono instances and instances already prepared as Mono."""
    if (instance.name or "").strip().lower() == "mono":
        return True
    fam = get_localized_family(instance)
    return bool(
        re.search(
            r"\bmono(?:\s+(?:unlicensed|variable))*$",
            fam.strip(),
            re.IGNORECASE,
        )
    )


def mono_family_name(base_family):
    """Append Mono once, so rerunning the script remains safe."""
    if re.search(r"(?i)(^|\s)mono$", base_family):
        return base_family
    return f"{base_family} Mono" if base_family else "Mono"


# ---------- main ----------

updated_trials = 0
updated_variables = 0
updated_statics = 0

for instance in font.instances:

    family_name = get_localized_family(instance)
    # detect
    is_trial = is_trial_instance(instance)
    is_variable = instance.type == INSTANCETYPEVARIABLE or is_variable_instance(instance)
    is_mono = is_mono_instance(instance)

    # Keep the source style named Mono, but export it as localized Regular.
    style_name = "Regular" if is_mono else (instance.name or "")
    if is_mono:
        instance.setProperty_value_languageTag_("styleNames", style_name, None)

    # --- build new base family name (LAB removed automatically) ---
    base_family = sanitize_name(font.familyName, keep_spaces=True)
    instance_base_family = mono_family_name(base_family) if is_mono else base_family

    if is_trial and is_variable:
        new_family_name = f"{instance_base_family} Unlicensed Variable"
    elif is_trial:
        new_family_name = f"{instance_base_family} Unlicensed"
    elif is_variable:
        new_family_name = f"{instance_base_family} Variable"
    else:
        new_family_name = instance_base_family

    # full name (LAB removed)
    full_name = sanitize_name(f"{new_family_name} {style_name}", keep_spaces=True)

    # --- write localized + PS names ---
    instance.setProperty_value_languageTag_("postscriptFullNames", full_name, None)

    # -------------------------------------------------------------
    # All instances share the global base-family folder and keep LABxx.
    # -------------------------------------------------------------
    export_family = sanitize_name(
        font.familyName,
        for_folder=True,
    )
    instance.customParameters["Export Folder"] = export_family

    # fileName logic
    # Keep family words together in file names: "Aktiv Sans" -> "AktivSans".
    clean_file_family = re.sub(r"[\s-]+", "", sanitize_name(instance_base_family))  # LAB removed

    if is_variable and not is_trial:
        file_name = f"{clean_file_family}-Variable"
    elif is_trial and not is_variable:
        file_name = sanitize_name(f"{clean_file_family}-{style_name}-Unlicensed")
    elif is_trial and is_variable:
        file_name = f"{clean_file_family}-Unlicensed-Variable"
    else:
        file_name = sanitize_name(f"{clean_file_family}-{style_name}")

    instance.customParameters["fileName"] = file_name
    instance.fontName = file_name

    # Set localized family name (LAB removed)
    clean_localized_family = sanitize_name(new_family_name, keep_spaces=True)
    instance.setProperty_value_languageTag_("familyNames", clean_localized_family, None)

    if is_mono or is_variable:
        instance.setProperty_value_languageTag_("styleMapFamilyNames", clean_localized_family, None)

    # --- variable-specific names ---
    if is_variable:
        # Remove LAB from the prefix base as well
        prefix_base = re.sub(r"[\s-]+", "", clean_file_family)  # Use clean_file_family instead of font.familyName
        variable_prefix = f"{prefix_base}Variable"
        instance.setProperty_value_languageTag_("variationsPostScriptNamePrefix", variable_prefix, None)

        instance.setProperty_value_languageTag_("styleMapStyleNames", style_name, None)
        instance.setProperty_value_languageTag_("preferredFamilyNames", clean_localized_family, None)
        instance.setProperty_value_languageTag_("preferredSubfamilyNames", style_name, None)
        
    # count
    if is_trial and is_variable:
        updated_trials += 1
        updated_variables += 1
    elif is_trial:
        updated_trials += 1
    elif is_variable:
        updated_variables += 1
    else:
        updated_statics += 1


print(
    f"✅ Updated {updated_trials} trial, {updated_variables} variable, and {updated_statics} static instances.\n"
    f"All familyNames now reflect '{font.familyName}'."
)
