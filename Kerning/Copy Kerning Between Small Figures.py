# MenuTitle: Copy Kerning Between Small Figures
# encoding: utf-8
__doc__ = """
Copy kerning between small figures.
"""

from GlyphsApp import *
from vanilla import *

font = Glyphs.font

# Define possible suffixes for each group (with descriptive names for UI)
groupSuffixes = {
    "Superior (.sups/superior)": [".sups", "superior"],
    "Inferior (.subs/inferior)": [".subs", "inferior"],
    "Numerator (.numr)": [".numr"],
    "Denominator (.dnom)": [".dnom"],
}

# Define expected categories/subCategories
groupCategories = {
    "Superior (.sups/superior)": ("Number", "Small"),
    "Inferior (.subs/inferior)": ("Number", "Small"),
    "Numerator (.numr)": ("Number", "Fraction"),
    "Denominator (.dnom)": ("Number", "Fraction"),
}

# Collect available groups
groups = {key: [] for key in groupSuffixes.keys()}

for g in font.glyphs:
    for groupName, suffixList in groupSuffixes.items():
        cat, subcat = groupCategories[groupName]
        if (
            (g.category == cat and g.subCategory == subcat)
            or any(g.name.endswith(suffix) for suffix in suffixList)
        ):
            groups[groupName].append(g.name)


class CopyKerningDialog(object):
    def __init__(self):
        availableGroups = [
            g for g, glyphs in groups.items() if len(glyphs) > 0
        ]

        if not availableGroups:
            Message("No small figure groups found in this font.")
            return

        self.availableGroups = availableGroups

        self.w = Window((350, 160), "Copy Kerning Between Small Figures")

        self.w.text = TextBox((15, 12, -15, 20), "Choose source group:")
        self.w.source = PopUpButton(
            (15, 40, -15, 20), availableGroups, sizeStyle="regular"
        )

        # ✅ Checkbox for all masters (default unchecked)
        self.w.allMasters = CheckBox(
            (15, 70, -15, 20),
            "Apply to all masters",
            value=False,
        )

        self.w.runButton = Button(
            (15, 110, -15, 20), "Copy Kerning", callback=self.copyKerning
        )

        self.w.open()
        self.w.makeKey()

    def copyKerning(self, sender):
        sourceGroup = self.availableGroups[self.w.source.get()]
        sourceSuffixes = groupSuffixes[sourceGroup]

        kerning = font.kerning

        # ✅ Decide which masters to process
        if self.w.allMasters.get():
            mastersToProcess = font.masters
        else:
            mastersToProcess = [(font.selectedLayers[0].master if font.selectedLayers else font.selectedFontMaster)]

        for master in mastersToProcess:
            masterID = master.id
            masterKerning = kerning[masterID]

            # Loop through kerning pairs
            for leftKey in list(masterKerning.keys()):
                for rightKey in list(masterKerning[leftKey].keys()):
                    value = masterKerning[leftKey][rightKey]

                    # Only process if both sides are from the source group
                    if any(
                        leftKey.endswith(suffix) for suffix in sourceSuffixes
                    ) and any(
                        rightKey.endswith(suffix) for suffix in sourceSuffixes
                    ):
                        # Copy to other groups
                        for targetGroup, targetSuffixes in groupSuffixes.items():
                            if targetGroup == sourceGroup:
                                continue
                            if not groups[targetGroup]:
                                continue  # skip if group not present

                            for targetSuffix in targetSuffixes:
                                newLeft = self.replaceSuffix(
                                    leftKey, sourceSuffixes, targetSuffix
                                )
                                newRight = self.replaceSuffix(
                                    rightKey, sourceSuffixes, targetSuffix
                                )

                                # Only copy if glyphs exist
                                leftName = newLeft.replace("@MMK_L_", "")
                                rightName = newRight.replace("@MMK_R_", "")

                                if leftName in font.glyphs and rightName in font.glyphs:
                                    font.setKerningForPair(
                                        masterID, newLeft, newRight, value
                                    )
                                    print(
                                        f"[{master.name}] Copied {value} "
                                        f"from {leftKey}/{rightKey} "
                                        f"to {newLeft}/{newRight}"
                                    )

        Glyphs.showNotification(
            "Kerning Copy Finished",
            f"Copied kerning from {sourceGroup} "
            f"({'all masters' if self.w.allMasters.get() else 'current master'}).",
        )

        # ✅ Close the dialog after finishing
        self.w.close()

    def replaceSuffix(self, name, sourceSuffixes, targetSuffix):
        """Replace any of the source suffixes with the target suffix."""
        for s in sourceSuffixes:
            if name.endswith(s):
                return name[: -len(s)] + targetSuffix
        return name


CopyKerningDialog()