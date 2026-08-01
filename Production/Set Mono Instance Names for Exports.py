# MenuTitle: Set Mono Instance Names for Exports
# -*- coding: utf-8 -*-
__doc__ = """
Finds instances named “Mono”, renames them to “Regular”, and updates their
localized family/style names, PostScript names, fileName, and Export Folder.
The family name receives a “Mono” suffix.
"""

from GlyphsApp import Glyphs, INSTANCETYPEVARIABLE
import re
import unicodedata


font = Glyphs.font
if not font:
	print("No font open.")
	raise SystemExit


def sanitize_name(value, for_folder=False, keep_spaces=False):
	if not value:
		return ""

	# Keep LABxx in export folder names, matching the existing production script.
	if not for_folder:
		value = re.sub(r"(?i)\bLAB\d{1,3}\b", "", value)

	value = unicodedata.normalize("NFKD", value)
	value = "".join(character for character in value if not unicodedata.combining(character))

	value = value.replace("’", "'").replace("‘", "'")
	value = value.replace("“", '"').replace("”", '"')
	value = value.replace("_", "-").replace("'", "")
	value = re.sub(r"[^A-Za-z0-9\s-]+", "-", value)

	value = value.strip()
	value = re.sub(r"\s+", " " if (for_folder or keep_spaces) else "-", value)
	value = re.sub(r"-+", "-", value).strip("-").strip()
	value = re.sub(r"\s{2,}", " ", value)
	return value


def get_localized_family(instance):
	"""Return localized or fallback family name safely."""
	family_name = None
	if instance.properties:
		for prop in instance.properties:
			if prop.key == "familyNames" and prop.defaultValue:
				family_name = prop.defaultValue
				break
	if not family_name:
		try:
			family_name = instance.customParameters["familyName"]
		except Exception:
			pass
	return family_name or font.familyName or ""


def is_trial_instance(instance):
	return bool(re.search(r"unlicensed\s*", get_localized_family(instance), re.IGNORECASE))


def is_variable_instance(instance):
	family_name = get_localized_family(instance)
	return instance.type == INSTANCETYPEVARIABLE or bool(
		re.search(r"\bvariable\b", family_name, re.IGNORECASE)
	)


def mono_family_name(base_family):
	"""Append Mono once, so the script remains safe if run on a prepared font."""
	if re.search(r"(?i)(^|\s)mono$", base_family):
		return base_family
	return "%s Mono" % base_family if base_family else "Mono"


updated = 0
for instance in font.instances:
	if (instance.name or "").strip().lower() != "mono":
		continue

	# Detect before changing the instance, just like the original script.
	is_trial = is_trial_instance(instance)
	is_variable = is_variable_instance(instance)

	# The Mono instance becomes the Regular style in the Mono family.
	instance.name = "Regular"
	style_name = "Regular"

	base_family = sanitize_name(font.familyName, keep_spaces=True)
	mono_family = mono_family_name(base_family)

	if is_trial and is_variable:
		new_family_name = "%s Unlicensed Variable" % mono_family
	elif is_trial:
		new_family_name = "%s Unlicensed" % mono_family
	elif is_variable:
		new_family_name = "%s Variable" % mono_family
	else:
		new_family_name = mono_family

	full_name = sanitize_name("%s %s" % (new_family_name, style_name), keep_spaces=True)
	instance.setProperty_value_languageTag_("postscriptFullNames", full_name, None)

	# Unlike the all-instance script, this export folder includes the Mono family.
	instance.customParameters["Export Folder"] = sanitize_name(
		mono_family, for_folder=True
	)

	# Keep family words together in file names, e.g. “Aktiv Sans Mono” ->
	# “AktivSansMono-Regular”.
	clean_file_family = re.sub(r"[\s-]+", "", sanitize_name(mono_family))

	if is_variable and not is_trial:
		file_name = "%s-Variable" % clean_file_family
	elif is_trial and not is_variable:
		file_name = sanitize_name("%s-%s-Unlicensed" % (clean_file_family, style_name))
	elif is_trial and is_variable:
		file_name = "%s-Unlicensed-Variable" % clean_file_family
	else:
		file_name = sanitize_name("%s-%s" % (clean_file_family, style_name))

	instance.customParameters["fileName"] = file_name
	instance.fontName = file_name

	clean_localized_family = sanitize_name(new_family_name, keep_spaces=True)
	instance.setProperty_value_languageTag_("familyNames", clean_localized_family, None)

	if is_variable:
		variable_prefix = "%sVariable" % clean_file_family
		instance.setProperty_value_languageTag_(
			"variationsPostScriptNamePrefix", variable_prefix, None
		)
		instance.setProperty_value_languageTag_(
			"styleMapFamilyNames", clean_localized_family, None
		)
		instance.setProperty_value_languageTag_("styleMapStyleNames", style_name, None)
		instance.setProperty_value_languageTag_(
			"preferredFamilyNames", clean_localized_family, None
		)
		instance.setProperty_value_languageTag_("preferredSubfamilyNames", style_name, None)

	updated += 1


if updated:
	print("✅ Updated %i Mono instance(s) to the Regular style." % updated)
	print("Family names now use the Mono suffix and export names were refreshed.")
else:
	print("No instance named Mono found.")
