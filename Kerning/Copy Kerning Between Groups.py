# MenuTitle: Copy Kerning Between Groups
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
import vanilla

class KerningCopyUI(object):
    def __init__(self):
        self.font = Glyphs.font
        if not self.font:
            print("No font open.")
            return

        self.master = (self.font.selectedLayers[0].master if self.font.selectedLayers else self.font.selectedFontMaster)
        self.kernDict = self.font.kerning[self.master.id]

        # ---- Collect groups from glyphs ----
        left = {}
        right = {}

        for g in self.font.glyphs:
            lg = g.leftKerningGroup
            rg = g.rightKerningGroup

            if isinstance(lg, str) and lg.strip():
                clean = lg.strip()
                left[clean]  = "@MMK_L_" + clean

            if isinstance(rg, str) and rg.strip():
                clean = rg.strip()
                right[clean] = "@MMK_R_" + clean

        # Merge clean names
        cleanNames = sorted(set(left.keys()) | set(right.keys()))

        # Failsafe: never let dropdown be empty
        if not cleanNames:
            cleanNames = ["(no groups found)"]

        self.cleanList = cleanNames
        self.leftMap   = left
        self.rightMap  = right

        # ---- Build UI ----
        self.w = vanilla.FloatingWindow((420, 240), "Copy Kerning Groups")

        y = 20; lh = 24

        self.w.text1 = vanilla.TextBox((20, y, 120, lh), "Source group:")
        self.w.source = vanilla.PopUpButton((150, y-2, 240, lh), self.cleanList)

        y += 40
        self.w.text2 = vanilla.TextBox((20, y, 120, lh), "Target group:")
        self.w.target = vanilla.PopUpButton((150, y-2, 240, lh), self.cleanList)

        y += 40
        self.w.text3 = vanilla.TextBox((20, y, 120, lh), "Side:")
        self.w.side = vanilla.PopUpButton(
            (150, y-2, 240, lh),
            ["Right → Right", "Left → Left", "Right → Left", "Left → Right"]
        )

        y += 50
        self.w.run = vanilla.Button((150, y, 120, 30), "Copy", callback=self.copyKerning)

        self.w.open()
        self.w.makeKey()

        # Debug output so we SEE what the script detected
        print("Clean groups:", self.cleanList)
        print("Left groups:", self.leftMap)
        print("Right groups:", self.rightMap)

    def copyKerning(self, sender):
        src = self.cleanList[self.w.source.get()]
        tgt = self.cleanList[self.w.target.get()]

        if src.startswith("(") or tgt.startswith("("):
            print("❌ No valid groups to copy.")
            return

        srcL = self.leftMap.get(src)
        srcR = self.rightMap.get(src)
        tgtL = self.leftMap.get(tgt)
        tgtR = self.rightMap.get(tgt)

        f = self.font
        mID = self.master.id
        count = 0
        mode = self.w.side.get()

        for leftKey, rightPairs in self.kernDict.items():
            for rightKey, value in rightPairs.items():

                if mode == 0 and rightKey == srcR:  # R → R
                    f.setKerningForPair(mID, leftKey, tgtR, value); count += 1

                elif mode == 1 and leftKey == srcL:  # L → L
                    f.setKerningForPair(mID, tgtL, rightKey, value); count += 1

                elif mode == 2 and rightKey == srcR:  # R → L
                    f.setKerningForPair(mID, tgtL, rightKey, value); count += 1

                elif mode == 3 and leftKey == srcL:  # L → R
                    f.setKerningForPair(mID, leftKey, tgtR, value); count += 1

        print(f"✅ Copied {count} pairs from {src} → {tgt}")
