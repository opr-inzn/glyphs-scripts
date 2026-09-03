# MenuTitle: Align to Cap Height
# -*- coding: utf-8 -*-

__doc__ = """
Vertically centers the contents of each selected glyph layer in its master’s
cap height. Anchors move with outlines and components, but only define the
bounds when a layer has no outlines or components.
"""

from Foundation import NSPoint


font = Glyphs.font
selected_layers = list(font.selectedLayers)
centered_count = 0


def vertical_bounds(layer):
	items = list(layer.paths) + list(layer.components)
	if items:
		min_y = min(item.bounds.origin.y for item in items)
		max_y = max(item.bounds.origin.y + item.bounds.size.height for item in items)
		return min_y, max_y

	anchors = list(layer.anchors)
	if anchors:
		anchor_positions = [anchor.position.y for anchor in anchors]
		return min(anchor_positions), max(anchor_positions)

	return None


if not selected_layers:
	print("You haven’t selected any glyphs to center.")
else:
	font.disableUpdateInterface()
	try:
		for layer in selected_layers:
			bounds = vertical_bounds(layer)
			if bounds is None:
				print(f"{layer.parent.name}: no contents to center on {layer.name}.")
				continue

			min_y, max_y = bounds
			move_y = layer.master.capHeight * 0.5 - (min_y + max_y) * 0.5

			layer.parent.beginUndo()
			try:
				for item in list(layer.paths) + list(layer.components):
					item.applyTransform((1.0, 0.0, 0.0, 1.0, 0.0, move_y))

				for anchor in layer.anchors:
					anchor.position = NSPoint(anchor.position.x, anchor.position.y + move_y)
			finally:
				layer.parent.endUndo()

			centered_count += 1
			print(f"Centered {layer.parent.name} on {layer.name} by {move_y:.1f} units.")
	finally:
		font.enableUpdateInterface()

	Glyphs.showNotification(
		"Vertically Center Selected Glyphs",
		f"Centered {centered_count} selected glyph layer(s) in the cap height.",
	)
