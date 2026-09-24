#MenuTitle: Show Kerning Pairs
# -*- coding: utf-8 -*-
__doc__="""
Show Kerning Pairs for this glyph in a new tab.
"""
import GlyphsApp
import traceback

thisFont = Glyphs.font
Doc = Glyphs.currentDocument
selectedLayers = list(thisFont.selectedLayers or [])

leftGroups = {}
rightGroups = {}
for g in thisFont.glyphs:
	if g.rightKerningGroup:
		group_name = g.rightKerningGroupId()
		try:
			leftGroups[group_name].append(g.name)
		except:
			leftGroups[group_name] = [g.name]

	if g.leftKerningGroup:
		group_name = g.leftKerningGroupId()
		try:
			rightGroups[group_name].append(g.name)
		except:
			rightGroups[group_name] = [g.name]

def nameMaker(kernGlyphOrGroup, side):
	# if this is a kerning group
	if kernGlyphOrGroup[0] == "@":
		# right glyph, left kerning group
		if side == "right":
			try:
				# return rightGroups[kernGlyphOrGroup][0]
				return sorted(rightGroups[kernGlyphOrGroup], key=len)[0]
			except:
				pass
		elif side == "left":
			# left glyph, right kerning group
			try:
				# return leftGroups[kernGlyphOrGroup][0]
				return sorted(leftGroups[kernGlyphOrGroup], key=len)[0]
			except:
				pass
	else:
		return thisFont.glyphForId_(kernGlyphOrGroup).name

# Keep both the pair lookup and the result tab on each selected layer’s master.
layersByMaster = {}
for layer in selectedLayers:
	layersByMaster.setdefault(layer.master.id, []).append(layer)

for masterID, masterLayers in layersByMaster.items():
	editStringsL = []
	editStringsR = []

	for thisLayer in masterLayers:
		thisGlyph = thisLayer.parent
		thisGlyphName = thisGlyph.name
		rGroupName = str(thisGlyph.rightKerningGroup)
		lGroupName = str(thisGlyph.leftKerningGroup)

		# print "\t", rGroupName, lGroupName

		kernPairListL = []
		kernPairListSortedL = []
		kernPairListR = []
		kernPairListSortedR = []

		for L in thisFont.kerning.get(masterID, {}).keys():
			try:
				# if the this kerning-pair's left glyph matches rGroupName (right side kerning group of thisGlyph)
				if rGroupName == L[7:] or rGroupName == thisFont.glyphForId_(L).name or thisFont.glyphForId_(L).name == thisGlyph.name:
					# for every R counterpart to L in the kerning pairs of rGroupName
					for R in thisFont.kerning[masterID][L].keys():
						if thisFont.kerning[masterID][L][R] != 0:
							kernPairListL += [nameMaker(R, "right")]
			except:
				# print traceback.format_exc()
				pass

			for R in thisFont.kerning[masterID][L].keys():
				try:
					# if the R counterpart (class glyph) of L glyph is the selectedGlyph
					if lGroupName == R[7:] or lGroupName == thisFont.glyphForId_(R).name or thisFont.glyphForId_(R).name == thisGlyph.name:
						if thisFont.kerning[masterID][L][R] != 0:
							kernPairListR += [nameMaker(L, "left")]
				except:
					pass

		kernPairListSortedL = [g.name for g in thisFont.glyphs if g.name in kernPairListL]
		for everyGlyph in kernPairListSortedL:
			editStringsL.append("/%s/%s" % (thisGlyphName, everyGlyph))

		kernPairListSortedR = [g.name for g in thisFont.glyphs if g.name in kernPairListR]
		for everyGlyph in kernPairListSortedR:
			editStringsR.append("/%s/%s" % (everyGlyph, thisGlyphName))


	editString = "\n".join(editStringsL) + "\n\n" + "\n".join(editStringsR)

	tab = thisFont.newTab(editString)
	tab.masterIndex = next(i for i, master in enumerate(thisFont.masters) if master.id == masterID)
