# MenuTitle: Add Font Info Parameters (Alexis Mark)
# -*- coding: utf-8 -*-

from datetime import datetime
import re
from GlyphsApp import GSCustomParameter

font = Glyphs.font

if not font:
    print("No font open!")

else:

    def custom_parameter(name, value, active=True):
        parameter = GSCustomParameter(name, value)
        parameter.active = active
        return parameter

    def font_name_without_date(name):
        return re.sub(r"\s+\d{6,8}$", "", name).strip()

    current_year = datetime.now().year
    display_font_name = font_name_without_date(font.familyName)

    # --------------------------------------------------
    # General Info
    # --------------------------------------------------

    font.designer = "Maximilian Inzinger"
    font.designerURL = "https://www.maximilianinzinger.com"

    font.manufacturer = "Bielke&Yang"
    font.manufacturerURL = "https://bielkeyang.com/"

    font.license = (
        "The font software and all related rights are protected by intellectual property law. Use is only permitted in compliance with the license terms. In particular, you are not allowed to reverse engineer, copy, modify, sell or sublicense the software, and you may not otherwise infringe the owner’s intellectual property rights."
    )

    font.copyright = (
        f"Copyright (c) {current_year} by Bielke&Yang. All rights reserved."
    )

    # --------------------------------------------------
    # Font Info properties
    # --------------------------------------------------

    font.setProperty_value_languageTag_("vendorID", "BY", None)
    font.setProperty_value_languageTag_("licenseURL", "https://bielkeyang.com/license", None)
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
