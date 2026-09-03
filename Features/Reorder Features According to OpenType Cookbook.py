# MenuTitle: Reorder Features According to OpenType Cookbook
# -*- coding: utf-8 -*-

__doc__ = """
Reorders recognized OpenType features according to the sequence recommended in
the OpenType Cookbook. Features not named by that sequence retain their exact
positions, and duplicate feature tags retain their relative order.
"""

import re

from GlyphsApp import Glyphs


ORDERED_GROUPS = (
	("locl",),
	("frac", "numr", "dnom"),
	("sups", "subs"),
	("lnum", "onum", "pnum", "tnum"),
	("ordn",),
	("smcp", "c2sc"),
	("case",),
	("cswh", "titl", "salt"),
	("rlig", "liga", "dlig"),
	("aalt",),
	("cpsp",),
)

FEATURE_RANK = {}
for group_index, group in enumerate(ORDERED_GROUPS):
	for tag_index, tag in enumerate(group):
		FEATURE_RANK[tag] = (group_index, tag_index)

STYLISTIC_SET_PATTERN = re.compile(r"^ss([0-9]{2})$")


def rank_for_tag(tag):
	if tag in FEATURE_RANK:
		return FEATURE_RANK[tag]

	match = STYLISTIC_SET_PATTERN.match(tag or "")
	if match:
		# Stylistic sets follow cswh, titl, and salt within the alternates group.
		return (7, 3 + int(match.group(1)))

	return None


def reordered_features(features):
	"""Reorder recognized features in place around untouched unknown features."""
	recognized = []
	for original_index, feature in enumerate(features):
		rank = rank_for_tag(feature.name)
		if rank is not None:
			recognized.append((rank, original_index, feature))

	ordered_recognized = [
		item[2]
		for item in sorted(recognized, key=lambda item: (item[0], item[1]))
	]
	ordered_iterator = iter(ordered_recognized)

	return [
		next(ordered_iterator) if rank_for_tag(feature.name) is not None else feature
		for feature in features
	]


font = Glyphs.font

if font is None:
	Glyphs.showNotification("Reorder Features", "No font is open.")
else:
	original_features = list(font.features)
	new_features = reordered_features(original_features)
	original_tags = [feature.name for feature in original_features]
	new_tags = [feature.name for feature in new_features]

	if new_tags == original_tags:
		message = "Feature order already matches the OpenType Cookbook sequence."
	else:
		font.disableUpdateInterface()
		try:
			font.features = new_features
		finally:
			font.enableUpdateInterface()

		moved_count = sum(
			old_feature is not new_feature
			for old_feature, new_feature in zip(original_features, new_features)
		)
		message = "Reordered %i feature position(s)." % moved_count

		print("Before: %s" % " ".join(original_tags))
		print("After:  %s" % " ".join(new_tags))

	Glyphs.showNotification("Reorder Features", message)
