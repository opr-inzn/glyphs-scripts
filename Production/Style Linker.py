# MenuTitle: Style Linker
# -*- coding: utf-8 -*-
__doc__ = """
Links upright and italic instances, sets Italic/Bold linkage,
assigns OS/2 weight classes, and synchronises Axis Location (Weight) for all instances.
"""

from GlyphsApp import Glyphs, GSCustomParameter
from Foundation import NSDictionary

font = Glyphs.font
if not font:
    raise Exception("No font open.")

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def is_variable_instance(inst):
    """Check if an instance is a variable instance."""
    try:
        # Check if the instance has the 'Variable Font' parameter
        if inst.customParameters:
            for param in inst.customParameters:
                if param.name == "Variable Font":
                    return True
        
        # Alternative: check if type is variable
        if hasattr(inst, "type") and inst.type == "variable":
            return True
            
    except Exception:
        pass
    return False

def is_italic_name(n):
    return n.endswith(" Italic")

def set_linkstyle_safe(inst, name):
    """Set linkStyle safely across Glyphs versions."""
    try:
        if hasattr(inst, "linkStyleName"):
            inst.linkStyleName = name
        if hasattr(inst, "linkStyle"):
            inst.linkStyle = name
    except Exception as e:
        print(f"⚠️ Could not set linkStyle for '{inst.name}': {e}")

def detect_weight_class(name, all_names):
    """Determine OS/2 weight class based on instance name and available names."""
    name = name.lower()
    has_hairline = any("hairline" in n.lower() for n in all_names)
    has_thin = any("thin" in n.lower() for n in all_names)

    if "hairline" in name:
        return 100 if has_thin else 250
    if "thin" in name:
        return 250 if has_hairline else 100
    if "light" in name:
        return 300
    if "medium" in name:
        return 500
    if "semibold" in name or "demibold" in name:
        return 600
    if "extrabold" in name or "heavy" in name:
        return 800
    if "bold" in name:
        return 700
    if "black" in name or "ultrablack" in name:
        return 900
    return None

def is_standard_weight_class(wc):
    """Check if weight class is a standard value."""
    standard_values = [100, 200, 300, 400, 500, 600, 700, 800, 900]
    return wc in standard_values

def get_axis_tags():
    """Get list of available axis tags in the font."""
    tags = []
    if hasattr(font, "axes") and font.axes:
        for axis in font.axes:
            if hasattr(axis, "axisTag"):
                tags.append(axis.axisTag)
    return tags

def get_axis_value(inst, axis_index):
    """Try to read an axis value safely by index."""
    try:
        if hasattr(inst, "axes") and inst.axes:
            if len(inst.axes) > axis_index:
                val = inst.axes[axis_index]
                if isinstance(val, (int, float)):
                    return float(val)
    except Exception:
        pass
    return None

def get_axis_index_by_tag(tag):
    """Find the index of an axis by its tag."""
    if hasattr(font, "axes") and font.axes:
        for i, axis in enumerate(font.axes):
            if hasattr(axis, "axisTag") and axis.axisTag == tag:
                return i
    return None


def ensure_axis_location_weight_only(inst, wc):
    """
    Add 'Axis Location' with weight if:
    - wght axis value ≠ weightClass, OR
    - weightClass is custom (not a standard 100-900 value)
    Remove existing Axis Location if they match and weight is standard.
    """
    available_axes = get_axis_tags()
    
    # Remove existing Axis Location parameter
    current_param = None
    if inst.customParameters:
        for p in inst.customParameters:
            if p.name == "Axis Location":
                current_param = p
                break
    
    # Only handle weight axis
    if "wght" in available_axes:
        wght_idx = get_axis_index_by_tag("wght")
        if wght_idx is not None:
            wght_val = get_axis_value(inst, wght_idx)
            is_custom = not is_standard_weight_class(wc)
            
            # Case 1: Custom weight class → always add Axis Location
            if is_custom:
                if current_param:
                    inst.customParameters.remove(current_param)
                
                axis_value = [{"Axis": "Weight", "Location": int(wc)}]
                inst.customParameters.append(GSCustomParameter("Axis Location", axis_value))
                print(f"Set Axis Location Weight={wc} for '{inst.name}' (custom weight class)")
                return True
            
            # Case 2: Standard weight, axis value matches → remove redundant entry
            if wght_val is not None and round(wght_val) == int(wc):
                if current_param:
                    inst.customParameters.remove(current_param)
                    print(f"Removed redundant Axis Location from '{inst.name}' (Weight matches {wc})")
                return False
            
            # Case 3: Standard weight, axis value differs → add Axis Location
            if current_param:
                inst.customParameters.remove(current_param)
            
            axis_value = [{"Axis": "Weight", "Location": int(wc)}]
            inst.customParameters.append(GSCustomParameter("Axis Location", axis_value))
            
            if wght_val is not None:
                print(f"Set Axis Location Weight={wc} for '{inst.name}' (axis={wght_val})")
            else:
                print(f"Set Axis Location Weight={wc} for '{inst.name}' (no axis value detected)")
            return True
    
    return False


# Filter out variable instances
static_instances = [inst for inst in font.instances if not is_variable_instance(inst)]
instances_by_name = {inst.name.strip(): inst for inst in static_instances}
all_names = list(instances_by_name.keys())

skipped_variable = len(font.instances) - len(static_instances)
if skipped_variable > 0:
    print(f"⏭️ Skipped {skipped_variable} variable instance(s)")

linked_count = 0
weight_set_count = 0
bold_linked_count = 0
axis_fixed_count = 0

# Print available axes for debugging
available_axes = get_axis_tags()
print(f"📊 Available axes in font: {', '.join(available_axes) if available_axes else 'none detected'}")

# ---------------------------------------------------------
# 1. Italic linking (FIRST - takes priority)
# ---------------------------------------------------------

italic_linked = set()  # Track which instances have been linked as italics

for inst in static_instances:
    base_name = inst.name.strip()
    if is_italic_name(base_name):
        continue

    italic_name = f"{base_name} Italic"
    italic = instances_by_name.get(italic_name)

    if italic:
        before_is_italic = getattr(italic, "isItalic", False)
        before_is_bold = getattr(italic, "isBold", False)
        before_link = getattr(italic, "linkStyle", None)

        is_bold_italic = italic.name.strip() == "Bold Italic"
        italic.isItalic = True
        italic.isBold = is_bold_italic
        italic_link_target = "Regular" if is_bold_italic else base_name
        set_linkstyle_safe(italic, italic_link_target)
        italic_linked.add(italic.name)  # Mark as linked

        after_is_italic = getattr(italic, "isItalic", False)
        after_is_bold = getattr(italic, "isBold", False)
        after_link = getattr(italic, "linkStyle", None)

        if (after_is_italic != before_is_italic) or (after_is_bold != before_is_bold) or (after_link != before_link):
            linked_count += 1
            if is_bold_italic:
                print(f"Linked '{italic.name}' → '{italic_link_target}' (bold and italic enabled)")
            else:
                print(f"Linked '{italic.name}' → '{base_name}' (italic enabled, bold disabled)")

# ---------------------------------------------------------
# 2. Weight classes + Axis Locations (all instances)
# ---------------------------------------------------------

for inst in static_instances:
    wc = detect_weight_class(inst.name, all_names)
    if wc is not None:
        if getattr(inst, "weightClass", None) != wc:
            inst.weightClass = wc
            weight_set_count += 1
            print(f"Set WeightClass {wc} for '{inst.name}'")

        if ensure_axis_location_weight_only(inst, wc):
            axis_fixed_count += 1
    else:
        # Check if instance already has a custom weightClass set
        existing_wc = getattr(inst, "weightClass", None)
        if existing_wc is not None:
            if ensure_axis_location_weight_only(inst, existing_wc):
                axis_fixed_count += 1

# ---------------------------------------------------------
# 3. Bold linkage (Regular or Book) - ONLY if not already italic-linked
# ---------------------------------------------------------

base = instances_by_name.get("Regular") or instances_by_name.get("Book")
bold = instances_by_name.get("Bold")

if base and bold:
    # Only set bold linking if it wasn't already linked as italic
    if bold.name not in italic_linked:
        bold.isBold = True
        bold.isItalic = False  # Explicitly set isItalic to False for bold links
        set_linkstyle_safe(bold, base.name)
        bold_linked_count += 1
        print(f"Linked 'Bold' as Bold of {base.name}")
    else:
        print(f"Skipped Bold linking for '{bold.name}' (already linked as italic)")

# ---------------------------------------------------------
# 4. Summary
# ---------------------------------------------------------

summary_msg = (
    f"Linked {linked_count} italics, set {weight_set_count} weights, "
    f"linked {bold_linked_count} bolds, updated {axis_fixed_count} Axis Locations"
)
if skipped_variable > 0:
    summary_msg += f", skipped {skipped_variable} variable"

Glyphs.showNotification(
    "Style Linker Finished",
    f"{summary_msg} (base: {base.name if base else 'none'})."
)
print(
    f"✅ Linked {linked_count} italics | Set {weight_set_count} weights | "
    f"Linked {bold_linked_count} bolds | Updated {axis_fixed_count} Axis Locations"
    + (f" | Skipped {skipped_variable} variable" if skipped_variable > 0 else "")
    + f" (base: {base.name if base else 'none'})."
)
