# MenuTitle: Enable Auto Alignment for Components
# -*- coding: utf-8 -*-
__doc__ = """
Enables automatic alignment for components in the selected layers.
"""

import GlyphsApp

Font = Glyphs.font
selectedLayers = list(Font.selectedLayers or [])

for layer in selectedLayers:
    glyph = layer.parent
    glyph.beginUndo()
    try:
        for component in layer.components:
            component.automaticAlignment = True
    finally:
        glyph.endUndo()

Glyphs.showNotification(
    "Enable Auto Alignment",
    f"Auto alignment enabled for components in {len(selectedLayers)} layer(s)."
)
