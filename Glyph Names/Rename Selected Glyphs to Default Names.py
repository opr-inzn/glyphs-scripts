# MenuTitle: Rename Selected Glyphs to Default Names
# -*- coding: utf-8 -*-

__doc__ = """
Renames selected glyphs using Glyphs’ standard names and known imported suffixes.
Uses Unicode for unsuffixed encoded glyphs; preserves variant suffixes and every
assigned Unicode value. Unknown names are reported, never guessed from outlines.
"""

from GlyphsApp import Glyphs


# Match whole suffixes so unrelated numbered variants are not collapsed.
SUFFIX_ALIASES = {"frac0": "numr", "frac0.002": "dnom"}


def default_name_for_glyph(glyph):
	name = glyph.name
	base, dot, suffix = name.partition(".")
	if base and suffix in SUFFIX_ALIASES:
		base = Glyphs.niceGlyphName(base) or base
		return base + "." + SUFFIX_ALIASES[suffix], "imported fraction suffix"

	# Preserve alternates even if they carry their base glyph’s Unicode.
	if not dot and glyph.unicode:
		info = Glyphs.glyphInfoForUnicode(glyph.unicode)
		if info and info.name:
			return info.name, "assigned Unicode"

	nice_name = Glyphs.niceGlyphName(name)
	if nice_name and nice_name != name:
		return nice_name, "Glyphs name alias"
	if base and dot:
		nice_base = Glyphs.niceGlyphName(base)
		if nice_base and nice_base != base:
			return nice_base + dot + suffix, "Glyphs base-name alias"
	return name, "no known conversion"


def rename_glyphs(font, glyphs):
	counts = {"renamed": 0, "unchanged": 0, "skipped": 0}
	font.disableUpdateInterface()
	try:
		for glyph in glyphs:
			old_name = glyph.name
			default_name, reason = default_name_for_glyph(glyph)
			if default_name == old_name:
				counts["unchanged"] += 1
				if reason == "no known conversion":
					print(f"Unchanged {old_name}: no known conversion; this does not confirm the name is standard.")
				continue
			existing = font.glyphs[default_name]
			if existing is not None and existing != glyph:
				print(f"Skipped {old_name}: {default_name} already exists.")
				counts["skipped"] += 1
				continue
			unicode_values = list(glyph.unicodes or [])
			glyph.beginUndo()
			try:
				glyph.name = default_name
				# Renaming can assign Unicode. Restore even an empty list.
				glyph.unicodes = unicode_values
			finally:
				glyph.endUndo()
			if glyph.name != default_name or list(glyph.unicodes or []) != unicode_values:
				raise RuntimeError(f"Could not preserve the requested name and Unicode values for {old_name}.")
			counts["renamed"] += 1
			print(f"Renamed {old_name} to {default_name} ({reason}); Unicode values preserved.")
	finally:
		font.enableUpdateInterface()
	return counts


def main():
	font = Glyphs.font
	if font is None:
		print("Open a font first.")
		return
	selected_glyphs = []
	for layer in font.selectedLayers or []:
		if layer.parent not in selected_glyphs:
			selected_glyphs.append(layer.parent)
	if not selected_glyphs:
		print("You haven’t selected any glyphs to rename.")
		return
	counts = rename_glyphs(font, selected_glyphs)
	summary = "Renamed {renamed}; unchanged {unchanged}; skipped {skipped}.".format(**counts)
	print(summary)
	Glyphs.showNotification("Rename Selected Glyphs", summary + " Details in Macro Panel.")


if __name__ == "__main__":
	main()
