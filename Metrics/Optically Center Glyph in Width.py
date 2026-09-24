# MenuTitle: Optically Center Glyph in Width
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

from GlyphsApp import Glyphs


CENTROID_WEIGHT = 0.7
BOUNDS_WEIGHT = 0.3
MIN_SHIFT = 0.01


def selected_edit_layers(font):
	layers = []
	seen = set()
	for layer in font.selectedLayers or []:
		if layer.parent is None:
			continue
		key = (layer.parent.name, layer.layerId)
		if key not in seen:
			layers.append(layer)
			seen.add(key)
	return layers


def decomposed_paths(layer):
	try:
		decomposedLayer = layer.copyDecomposedLayer()
		if decomposedLayer and decomposedLayer.paths:
			return decomposedLayer.paths
	except Exception:
		pass

	return layer.paths


def contour_area_and_centroid(path):
	if not path.closed:
		return 0.0, 0.0

	points = [(node.x, node.y) for node in path.nodes]
	pointCount = len(points)

	if pointCount < 3:
		return 0.0, 0.0

	area = 0.0
	centerX = 0.0

	for index in range(pointCount):
		x0, y0 = points[index]
		x1, y1 = points[(index + 1) % pointCount]
		cross = x0 * y1 - x1 * y0
		area += cross
		centerX += (x0 + x1) * cross

	area *= 0.5
	if abs(area) < 0.0001:
		return 0.0, 0.0

	centerX /= 6.0 * area
	return area, centerX


def optical_center_x(layer):
	bounds = layer.bounds
	if bounds.size.width <= 0:
		return None

	boundsCenterX = bounds.origin.x + bounds.size.width * 0.5
	totalArea = 0.0
	weightedCenterX = 0.0

	for path in decomposed_paths(layer):
		area, centerX = contour_area_and_centroid(path)
		if area:
			totalArea += area
			weightedCenterX += centerX * area

	if abs(totalArea) < 0.0001:
		return boundsCenterX

	centroidX = weightedCenterX / totalArea
	return centroidX * CENTROID_WEIGHT + boundsCenterX * BOUNDS_WEIGHT


def optically_center_layer(layer):
	centerX = optical_center_x(layer)
	if centerX is None:
		print("%s: no outline bounds found" % layer.parent.name)
		return False

	targetX = layer.width * 0.5
	shiftX = targetX - centerX

	if abs(shiftX) < MIN_SHIFT:
		print("%s: already optically centered" % layer.parent.name)
		return False

	layer.applyTransform((1, 0, 0, 1, shiftX, 0))
	print("%s: shifted %.1f units" % (layer.parent.name, shiftX))
	return True


font = Glyphs.font
if not font:
	raise Exception("No font open.")

font.disableUpdateInterface()

try:
	changedCount = 0
	selectedLayers = selected_edit_layers(font)

	for layer in selectedLayers:
		if optically_center_layer(layer):
			changedCount += 1
finally:
	font.enableUpdateInterface()

Glyphs.redraw()
Glyphs.showNotification(
	"Optically Center Glyph",
	"Centered %i selected layer(s)." % changedCount,
)
