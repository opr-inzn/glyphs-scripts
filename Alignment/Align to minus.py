# MenuTitle: Align to Minus
# -*- coding: utf-8 -*-

def alignMinus():
    font = Glyphs.font
    minusGlyph = font.glyphs["minus"]
    if not minusGlyph:
        print("No 'minus' glyph found in this font.")
        return

    font.disableUpdateInterface()  # to speed things up and avoid flicker

    for layer in font.selectedLayers:
        parentGlyph = layer.parent
        minusLayer = minusGlyph.layers[layer.layerId]
        if not minusLayer:
            print(f"No minus layer found for {parentGlyph.name} in layer {layer.name}")
            continue

        # Vertical centers from bounds
        minusCenterY = minusLayer.bounds.origin.y + minusLayer.bounds.size.height * 0.5
        glyphCenterY = layer.bounds.origin.y + layer.bounds.size.height * 0.5
        deltaY = minusCenterY - glyphCenterY

        if abs(deltaY) < 0.01:
            print(f"{parentGlyph.name}: already aligned")
            continue

        # Move paths (nodes)
        for path in layer.paths:
            for node in path.nodes:
                node.y += deltaY

        # Move components
        for comp in layer.components:
            pos = comp.position
            comp.position = (pos.x, pos.y + deltaY)

        print(f"Aligned {parentGlyph.name} on {layer.name} by {deltaY:.1f} units")

    font.enableUpdateInterface()

# Run the function
alignMinus()
