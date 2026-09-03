#MenuTitle: Remove Manual Glyph Info

from GlyphsApp import Glyphs

font = Glyphs.font
glyphs = list({layer.parent for layer in font.selectedLayers})

font.disableUpdateInterface()

for glyph in glyphs:
	glyph.beginUndo()

	glyph.storeCategory = False
	glyph.storeSubCategory = False
	glyph.storeCase = False
	glyph.storeScript = False
	glyph.storeProductionName = False
	glyph.storeSortName = False

	if hasattr(glyph, "storeDirection"):
		glyph.storeDirection = False

	glyph.updateGlyphInfo()

	glyph.endUndo()

font.enableUpdateInterface()

print("Removed manual glyph info for %i glyphs." % len(glyphs))
