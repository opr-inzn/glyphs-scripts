# MenuTitle: Disable Auto Alignment for Components
# -*- coding: utf-8 -*-
__doc__ = """
Disables automatic alignment for components in the selected layers.
"""

import GlyphsApp

Font = Glyphs.font
selectedLayers = list(Font.selectedLayers or [])

for layer in selectedLayers:
    glyph = layer.parent
    glyph.beginUndo()
    try:
        for component in layer.components:
            component.automaticAlignment = False
    finally:
        glyph.endUndo()

Glyphs.showNotification(
    "Disable Auto Alignment",
    f"Auto alignment disabled for components in {len(selectedLayers)} layer(s)."
)
