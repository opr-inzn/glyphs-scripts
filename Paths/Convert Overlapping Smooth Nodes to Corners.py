#MenuTitle: Convert Overlapping Smooth Nodes to Corners
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

__doc__ = """
For each selected glyph, compares all on-curve nodes in master and special
layers. If a green smooth node occupies the same position as a blue corner
node, the smooth node is changed to a corner node.
"""

from GlyphsApp import Glyphs, OFFCURVE


POSITION_TOLERANCE = 0.01


def selected_glyphs(font):
	glyphs = []
	seen = set()

	for layer in font.selectedLayers:
		glyph = layer.parent
		if glyph is not None and glyph.name not in seen:
			glyphs.append(glyph)
			seen.add(glyph.name)

	return glyphs


def relevant_layers(glyph):
	return [
		layer
		for layer in glyph.layers
		if layer.isMasterLayer or layer.isSpecialLayer
	]


def same_position(first_node, second_node):
	return (
		abs(first_node.position.x - second_node.position.x) <= POSITION_TOLERANCE
		and abs(first_node.position.y - second_node.position.y) <= POSITION_TOLERANCE
	)


def coincident_smooth_nodes(glyph):
	layers = relevant_layers(glyph)
	nodes = []

	for layer in layers:
		for path_index, path in enumerate(layer.paths):
			for node_index, node in enumerate(path.nodes):
				if node.type != OFFCURVE:
					nodes.append((layer, path_index, node_index, node))

	corner_nodes = [node for layer, path_index, node_index, node in nodes if not node.smooth]
	return [
		(layer, path_index, node_index, node)
		for layer, path_index, node_index, node in nodes
		if node.smooth
		and any(same_position(node, corner_node) for corner_node in corner_nodes)
	]


font = Glyphs.font
if font is None:
	Glyphs.showNotification(
		"Convert Overlapping Smooth Nodes",
		"No font open.",
	)
else:
	glyphs = selected_glyphs(font)
	if not glyphs:
		Glyphs.showNotification(
			"Convert Overlapping Smooth Nodes",
			"No glyphs selected.",
		)
	else:
		changed_nodes = 0
		changed_glyphs = 0

		font.disableUpdateInterface()
		try:
			for glyph in glyphs:
				matches = coincident_smooth_nodes(glyph)
				if not matches:
					continue

				glyph.beginUndo()
				try:
					for layer, path_index, node_index, node in matches:
						node.smooth = False
						print(
							"%s, %s: path %i, node %i changed to corner"
							% (
								glyph.name,
								layer.name,
								path_index + 1,
								node_index + 1,
							)
						)
				finally:
					glyph.endUndo()

				changed_nodes += len(matches)
				changed_glyphs += 1
		finally:
			font.enableUpdateInterface()

		Glyphs.redraw()
		Glyphs.showNotification(
			"Convert Overlapping Smooth Nodes",
			"Changed %i node(s) in %i of %i selected glyph(s)."
			% (changed_nodes, changed_glyphs, len(glyphs)),
		)
