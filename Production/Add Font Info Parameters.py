# MenuTitle: Add Font Info Parameters
# -*- coding: utf-8 -*-

from datetime import datetime
from GlyphsApp import GSCustomParameter

font = Glyphs.font

if not font:
    print("No font open!")

else:

    def custom_parameter(name, value, active=True):
        parameter = GSCustomParameter(name, value)
        parameter.active = active
        return parameter

    current_year = datetime.now().year

    # --------------------------------------------------
    # General Info
    # --------------------------------------------------

    font.designer = "Maximilian Inzinger"
    font.designerURL = "https://www.maximilianinzinger.com"

    font.manufacturer = "Office of Personal Responsibility"
    font.manufacturerURL = "https://www.maximilianinzinger.com"

    font.license = (
        "Lawful use of the fonts or the data contained within the font files excludes modifying, reassembling, renaming, storing on publicly available servers, redistibutring and selling. Any unlawful use of this typographic software will be prosecuted. For additional information contact office@maximilianinzinger.com."
    )

    font.copyright = (
        f"Copyright (c) {current_year} by Office of Personal Responsibility (Maximilian Inzinger). All rights reserved."
    )

    # --------------------------------------------------
    # Font Info properties
    # --------------------------------------------------
    
    font.setProperty_value_languageTag_("vendorID", "OPR", None)
    font.setProperty_value_languageTag_("licenseURL", "https://maximilianinzinger.com/license", None)
    font.setProperty_value_languageTag_("versionString", "Version %d.%03d", None)

    # --------------------------------------------------
    # Font-level custom parameters
    # --------------------------------------------------

    font.customParameters["Use Typo Metrics"] = True

    if len(font.masters) > 1:
        font.customParameters["Family Alignment Zones"] = []

    font.customParameters["panose"] = [
        0, 0, 0, 0, 0,
        0, 0, 0, 0, 0
    ]

    font.customParameters["fsType"] = 3

    # --------------------------------------------------
    # Optional disabled parameters
    # --------------------------------------------------

    if not any(
        parameter.name == "unicodeRanges"
        for parameter in font.customParameters
    ):
        font.customParameters.append(
            custom_parameter(
                "unicodeRanges",
                [],
                active=False
            )
        )
    else:
        print("ℹ️ 'unicodeRanges' already exists — skipping.")

    if not any(
        parameter.name == "codePageRanges"
        for parameter in font.customParameters
    ):
        font.customParameters.append(
            custom_parameter(
                "codePageRanges",
                [],
                active=False
            )
        )
    else:
        print("ℹ️ 'codePageRanges' already exists — skipping.")

    # --------------------------------------------------
    # Features
    # --------------------------------------------------

    font.customParameters["Update Features"] = True

    # --------------------------------------------------
    # Compatibility
    # --------------------------------------------------

    if len(font.masters) > 1:
        font.customParameters["Enforce Compatibility Check"] = True

    print("✅ Font info parameters added.")