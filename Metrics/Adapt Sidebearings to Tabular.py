#MenuTitle: Adapt Sidebearings to Tabular
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

__doc__ = """
For each selected glyph, positions its matching .tf glyph on the selected
layer’s master the way the base glyph sits in its own width, keeping the .tf
glyph’s existing advance width. The width the .tf glyph gains or loses is split
equally between both sides, so the outline keeps the base glyph’s left/right
offset (e.g. 7 at 40/10 in a 50-unit-wider cell becomes 65/35, not 80/20).

If the .tf outline is a different width from the base outline (e.g. a 1 with
a foot serif), sidebearings can’t transfer exactly; check those glyphs by eye
or run Optically Center Glyph in Width afterwards.

Selecting either cent or cent.tf targets cent.tf and reads spacing from cent.
"""

from GlyphsApp import Glyphs


TARGET_SUFFIX = ".tf"


def adapted_sidebearings(source_lsb, source_rsb, total_target_sidebearings):
	# Split the width difference equally between both sides, which keeps the
	# source’s LSB − RSB offset. Scaling the sidebearings by their ratio instead
	# exaggerates asymmetry: a 7 at 40/10 would get four times as much extra
	# space on the left as on the right and look pushed against the next figure.
	source_difference = source_lsb - source_rsb
	new_lsb = round((total_target_sidebearings + source_difference) * 0.5)
	new_rsb = total_target_sidebearings - new_lsb
	return new_lsb, new_rsb


BLACK_WIDTH_TOLERANCE = 0.05


def selected_base_glyphs_and_masters(font):
	glyph_names = []
	seen = set()

	for selected_layer in font.selectedLayers:
		glyph = selected_layer.parent
		if glyph is None:
			continue

		glyph_name = glyph.name
		if glyph_name.endswith(TARGET_SUFFIX):
			glyph_name = glyph_name[:-len(TARGET_SUFFIX)]

		master = selected_layer.master
		key = (glyph_name, master.id)
		if glyph_name and key not in seen:
			glyph_names.append((glyph_name, master))
			seen.add(key)

	return glyph_names


def adapt_tf_sidebearings(font, master, base_glyph_name):
	target_glyph_name = base_glyph_name + TARGET_SUFFIX
	source_glyph = font.glyphs[base_glyph_name]
	target_glyph = font.glyphs[target_glyph_name]

	if source_glyph is None:
		return False, "%s: base glyph is missing" % base_glyph_name
	if target_glyph is None:
		return False, "%s: target glyph is missing" % target_glyph_name

	source_layer = source_glyph.layers[master.id]
	target_layer = target_glyph.layers[master.id]
	if source_layer is None or target_layer is None:
		return False, "%s: source or target layer is missing" % target_glyph_name

	target_bounds = target_layer.bounds
	if target_bounds is None or target_bounds.size.width <= 0:
		return False, "%s: target layer has no usable outline" % target_glyph_name

	target_width = target_layer.width
	target_black_width = target_bounds.size.width
	total_target_sidebearings = target_width - target_black_width
	new_lsb, new_rsb = adapted_sidebearings(
		source_layer.LSB,
		source_layer.RSB,
		total_target_sidebearings,
	)

	source_bounds = source_layer.bounds
	source_black_width = source_bounds.size.width if source_bounds else 0
	shape_note = ""
	if source_black_width > 0 and abs(
		target_black_width - source_black_width
	) > BLACK_WIDTH_TOLERANCE * source_black_width:
		shape_note = " – outline width differs (%s vs %s), check visually" % (
			round(source_black_width),
			round(target_black_width),
		)

	target_glyph.beginUndo()
	try:
		target_layer.LSB = new_lsb
		# Setting a sidebearing can affect advance width. Restore the defined
		# tabular width last so the script cannot leave it changed.
		target_layer.width = target_width
	finally:
		target_glyph.endUndo()

	print(
		"%s -> %s (%s): L/R %s/%s -> %s/%s, width kept at %s%s"
		% (
			base_glyph_name,
			target_glyph_name,
			master.name,
			source_layer.LSB,
			source_layer.RSB,
			new_lsb,
			new_rsb,
			target_width,
			shape_note,
		)
	)
	return True, None


font = Glyphs.font
if font is None:
	Glyphs.showNotification("Adapt Sidebearings to Tabular", "No font open.")
else:
	base_glyph_names = selected_base_glyphs_and_masters(font)

	if not base_glyph_names:
		Glyphs.showNotification("Adapt Sidebearings to Tabular", "No glyphs selected.")
	else:
		changed = 0
		skipped = []

		font.disableUpdateInterface()
		try:
			for base_glyph_name, master in base_glyph_names:
				did_change, skip_message = adapt_tf_sidebearings(
					font, master, base_glyph_name
				)
				if did_change:
					changed += 1
				elif skip_message:
					skipped.append(skip_message)
		finally:
			font.enableUpdateInterface()

		message = "Updated %i .tf layer(s) on the selected layers’ masters." % changed
		if skipped:
			message += "\n\nSkipped:\n" + "\n".join(skipped[:10])
			if len(skipped) > 10:
				message += "\n...and %i more." % (len(skipped) - 10)

		Glyphs.showNotification("Adapt Sidebearings to Tabular", message)
