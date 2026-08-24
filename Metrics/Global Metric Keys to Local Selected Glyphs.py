#MenuTitle: Global Metric Keys to Local Keys
# -*- coding: utf-8 -*-
__doc__ = """
Moves glyph-level metric keys to layers for selected glyphs only, so they
become layer-specific ('==' in the Glyphs UI). Existing layer-specific
overrides are left untouched.
"""

from GlyphsApp import Glyphs


font = Glyphs.font
count = 0
skipped = 0


def selected_glyphs(font):
	glyphs = []
	seen = set()
	for layer in font.selectedLayers:
		glyph = layer.parent
		if glyph and glyph.name not in seen:
			glyphs.append(glyph)
			seen.add(glyph.name)
	return glyphs


def migrate_key(glyph, attr_name, label):
	global count, skipped

	glyph_value = getattr(glyph, attr_name, None)
	if not glyph_value:
		return
	if glyph_value == "=|":
		print("  [%s] kept glyph-level %s: '=|'" % (glyph.name, label))
		return

	applied_layers = 0
	for layer in glyph.layers:
		if not layer.isMasterLayer and not layer.isSpecialLayer:
			continue

		layer_value = getattr(layer, attr_name, None)
		if layer_value:
			skipped += 1
			print(
				"  [%s / %s] skipped %s; layer already has '%s'"
				% (glyph.name, layer.name, label, layer_value)
			)
			continue

		setattr(layer, attr_name, glyph_value)
		applied_layers += 1
		count += 1
		print(
			"  [%s / %s] %s: '%s' -> layer key"
			% (glyph.name, layer.name, label, glyph_value)
		)

	if applied_layers:
		setattr(glyph, attr_name, None)
		print("  [%s] cleared glyph-level %s: '%s'" % (glyph.name, label, glyph_value))


if font is None:
	print("No font open.")
else:
	glyphs = selected_glyphs(font)

	if not glyphs:
		print("No glyphs selected.")
	else:
		font.disableUpdateInterface()
		try:
			for glyph in glyphs:
				glyph.beginUndo()
				try:
					migrate_key(glyph, "leftMetricsKey", "leftMetricsKey")
					migrate_key(glyph, "rightMetricsKey", "rightMetricsKey")
					migrate_key(glyph, "widthMetricsKey", "widthMetricsKey")
				finally:
					glyph.endUndo()
		finally:
			font.enableUpdateInterface()

		print(
			"\nDone. Checked %i selected glyph(s); moved %i metric key assignment(s) to layers."
			% (len(glyphs), count)
		)
		if skipped:
			print("Skipped %i layer(s) that already had their own key." % skipped)
		if count == 0 and skipped == 0:
			print("No glyph-level metric keys found on selected glyphs.")
