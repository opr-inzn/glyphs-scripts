#MenuTitle: Duplicate Nodes on Top
# -*- coding: utf-8 -*-
__doc__ = "Duplicates selected on-curve nodes in place and converts them to corner nodes."

from GlyphsApp import Glyphs, GSNode, OFFCURVE, LINE

font = Glyphs.font
layer = font.selectedLayers[0]

layer.beginChanges()

try:
    # Copy selection first because we are modifying the paths
    selection = list(layer.selection)

    for node in selection:
        if isinstance(node, GSNode) and node.type != OFFCURVE:

            # Turn original smooth node into corner
            node.smooth = False

            # Duplicate node at exactly the same position
            newNode = node.copy()
            newNode.type = LINE
            newNode.smooth = False

            # Insert directly after original
            node.parent.nodes.insert(node.index + 1, newNode)

finally:
    layer.endChanges()