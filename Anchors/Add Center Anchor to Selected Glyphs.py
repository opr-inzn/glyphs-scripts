#MenuTitle: Add _center Anchor to Selected Glyphs
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

__doc__ = """
Adds or updates a _center anchor on the current master layer of every selected
glyph. Numerator glyphs share the Y position from zero.numr; other glyphs use
their own mathematical vertical center. Each glyph’s X position is its own
curve-aware area centroid, blended slightly toward the outline bounds center
for optical stability.
"""

from AppKit import NSPoint
from GlyphsApp import CURVE, GSAnchor, Glyphs, OFFCURVE


ANCHOR_NAME = "_center"
REFERENCE_GLYPH_NAME = "zero.numr"
NUMERATOR_SUFFIX = ".numr"
CENTROID_WEIGHT = 0.7
BOUNDS_WEIGHT = 0.3
CURVE_STEPS = 24


def selected_current_master_layers(font):
	master_id = font.selectedFontMaster.id
	layers = []
	seen_glyph_names = set()

	for selected_layer in font.selectedLayers:
		glyph = selected_layer.parent
		if glyph is None or glyph.name in seen_glyph_names:
			continue

		layer = glyph.layers[master_id]
		if layer is not None:
			layers.append(layer)
			seen_glyph_names.add(glyph.name)

	return layers


def decomposed_paths(layer):
	try:
		decomposed_layer = layer.copyDecomposedLayer()
		if decomposed_layer is not None and decomposed_layer.paths:
			return decomposed_layer.paths
	except Exception:
		pass

	return layer.paths


def cubic_point(p0, p1, p2, p3, t):
	one_minus_t = 1.0 - t
	return (
		one_minus_t ** 3 * p0[0]
		+ 3.0 * one_minus_t ** 2 * t * p1[0]
		+ 3.0 * one_minus_t * t ** 2 * p2[0]
		+ t ** 3 * p3[0],
		one_minus_t ** 3 * p0[1]
		+ 3.0 * one_minus_t ** 2 * t * p1[1]
		+ 3.0 * one_minus_t * t ** 2 * p2[1]
		+ t ** 3 * p3[1],
	)


def flattened_contour_points(path):
	if not path.closed:
		return []

	nodes = list(path.nodes)
	if len(nodes) < 3:
		return []

	first_oncurve_index = None
	for index, node in enumerate(nodes):
		if node.type != OFFCURVE:
			first_oncurve_index = index
			break

	if first_oncurve_index is None:
		return []

	first_node = nodes[first_oncurve_index]
	current_point = (first_node.x, first_node.y)
	points = [current_point]
	controls = []

	for offset in range(1, len(nodes) + 1):
		node = nodes[(first_oncurve_index + offset) % len(nodes)]
		if node.type == OFFCURVE:
			controls.append((node.x, node.y))
			continue

		end_point = (node.x, node.y)
		if node.type == CURVE and len(controls) == 2:
			for step in range(1, CURVE_STEPS + 1):
				t = step / float(CURVE_STEPS)
				points.append(
					cubic_point(
						current_point,
						controls[0],
						controls[1],
						end_point,
						t,
					)
				)
		else:
			points.append(end_point)

		current_point = end_point
		controls = []

	return points


def contour_area_and_center_x(path):
	points = flattened_contour_points(path)

	point_count = len(points)
	if point_count < 3:
		return 0.0, 0.0

	area = 0.0
	center_x = 0.0
	for index in range(point_count):
		x0, y0 = points[index]
		x1, y1 = points[(index + 1) % point_count]
		cross = x0 * y1 - x1 * y0
		area += cross
		center_x += (x0 + x1) * cross

	area *= 0.5
	if abs(area) < 0.0001:
		return 0.0, 0.0

	center_x /= 6.0 * area
	return area, center_x


def optical_center_x(layer):
	bounds = layer.bounds
	if bounds.size.width <= 0:
		return None

	bounds_center_x = bounds.origin.x + bounds.size.width * 0.5
	total_area = 0.0
	weighted_center_x = 0.0

	for path in decomposed_paths(layer):
		area, center_x = contour_area_and_center_x(path)
		if area:
			total_area += area
			weighted_center_x += center_x * area

	if abs(total_area) < 0.0001:
		return bounds_center_x

	centroid_x = weighted_center_x / total_area
	return centroid_x * CENTROID_WEIGHT + bounds_center_x * BOUNDS_WEIGHT


def numerator_reference_y(font):
	reference_glyph = font.glyphs[REFERENCE_GLYPH_NAME]
	if reference_glyph is None:
		return None, "%s is missing from the font" % REFERENCE_GLYPH_NAME

	reference_layer = reference_glyph.layers[font.selectedFontMaster.id]
	if reference_layer is None:
		return None, "%s has no layer for the current master" % REFERENCE_GLYPH_NAME

	reference_anchor = reference_layer.anchorForName_(ANCHOR_NAME)
	if reference_anchor is not None:
		return reference_anchor.position.y, None

	bounds = reference_layer.bounds
	if bounds.size.height <= 0:
		return None, "%s has no usable outline bounds" % REFERENCE_GLYPH_NAME

	return bounds.origin.y + bounds.size.height * 0.5, None


def center_position(layer, numerator_anchor_y):
	bounds = layer.bounds
	if bounds.size.width <= 0 or bounds.size.height <= 0:
		return None

	x = optical_center_x(layer)
	if layer.parent.name.endswith(NUMERATOR_SUFFIX):
		if numerator_anchor_y is None:
			return None
		anchor_y = numerator_anchor_y
	else:
		anchor_y = bounds.origin.y + bounds.size.height * 0.5

	return NSPoint(x, anchor_y)


def add_or_update_anchor(layer, numerator_anchor_y):
	position = center_position(layer, numerator_anchor_y)
	if position is None:
		print("%s: skipped; no usable outline bounds" % layer.parent.name)
		return False

	anchor = layer.anchorForName_(ANCHOR_NAME)
	if anchor is None:
		anchor = GSAnchor(ANCHOR_NAME, position)
		layer.addAnchor_(anchor)
		action = "added"
	else:
		anchor.setPosition_(position)
		action = "updated"

	print(
		"%s: %s %s at %.1f, %.1f"
		% (layer.parent.name, action, ANCHOR_NAME, position.x, position.y)
	)
	return True


font = Glyphs.font
if font is None:
	Glyphs.showNotification("Add _center Anchor", "No font open.")
else:
	layers = selected_current_master_layers(font)
	if not layers:
		Glyphs.showNotification("Add _center Anchor", "No glyphs selected.")
	else:
		numerator_layers = [
			layer
			for layer in layers
			if layer.parent.name.endswith(NUMERATOR_SUFFIX)
		]
		numerator_anchor_y = None
		numerator_error = None
		if numerator_layers:
			numerator_anchor_y, numerator_error = numerator_reference_y(font)

		changed_count = 0
		skipped_count = 0
		font.disableUpdateInterface()
		try:
			for layer in layers:
				glyph = layer.parent
				if glyph.name.endswith(NUMERATOR_SUFFIX) and numerator_error:
					print("%s: skipped; %s" % (glyph.name, numerator_error))
					skipped_count += 1
					continue

				glyph.beginUndo()
				try:
					if add_or_update_anchor(layer, numerator_anchor_y):
						changed_count += 1
					else:
						skipped_count += 1
				finally:
					glyph.endUndo()
		finally:
			font.enableUpdateInterface()

		Glyphs.redraw()
		message = "Updated %i _center anchor(s)." % changed_count
		if skipped_count:
			message += " Skipped %i glyph(s); see Macro Panel." % skipped_count
		Glyphs.showNotification("Add _center Anchor", message)
