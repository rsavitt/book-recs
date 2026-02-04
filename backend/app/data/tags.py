"""
Tag and trope definitions for Romantasy classification.

Categories:
- genre: High-level genre tags
- trope: Common romance/fantasy tropes
- setting: World/setting types
- theme: Thematic elements
"""

# Tags that strongly indicate a book is Romantasy
ROMANTASY_INDICATOR_TAGS = {
    # Direct indicators
    "romantasy",
    "fantasy-romance",
    "romantic-fantasy",
    "fae-romance",
    "fantasy-with-romance",
    # Setting indicators
    "fae",
    "faerie",
    "fairy",
    "dragons",
    "dragon-riders",
    "shifters",
    "vampires",
    "witches",
    "magic-academy",
    "fantasy-academy",
    # Trope indicators (when combined with fantasy elements)
    "enemies-to-lovers",
    "forced-proximity",
    "slow-burn",
    "spicy-fantasy",
    "smutty-fantasy",
}

# Tags that suggest but don't confirm Romantasy
ROMANTASY_SUPPORTING_TAGS = {
    "high-fantasy",
    "epic-fantasy",
    "urban-fantasy",
    "paranormal",
    "paranormal-romance",
    "dark-romance",
    "new-adult",
    "adult-fantasy",
    "ya-fantasy",
    "romance",
    "fantasy",
}

# Full tag definitions with metadata
TAGS = [
    # === GENRE TAGS ===
    {
        "name": "Romantasy",
        "slug": "romantasy",
        "category": "genre",
        "description": "Fantasy with a central romance plot",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Fantasy Romance",
        "slug": "fantasy-romance",
        "category": "genre",
        "description": "Romance set in a fantasy world",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Paranormal Romance",
        "slug": "paranormal-romance",
        "category": "genre",
        "description": "Romance with supernatural elements (vampires, werewolves, etc.)",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Urban Fantasy",
        "slug": "urban-fantasy",
        "category": "genre",
        "description": "Fantasy set in a modern urban environment",
        "is_romantasy_indicator": False,
    },
    {
        "name": "High Fantasy",
        "slug": "high-fantasy",
        "category": "genre",
        "description": "Epic fantasy in a fully imagined world",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Dark Fantasy",
        "slug": "dark-fantasy",
        "category": "genre",
        "description": "Fantasy with darker themes and moral ambiguity",
        "is_romantasy_indicator": False,
    },
    {
        "name": "YA Fantasy",
        "slug": "ya-fantasy",
        "category": "genre",
        "description": "Fantasy written for young adult readers",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Adult Fantasy",
        "slug": "adult-fantasy",
        "category": "genre",
        "description": "Fantasy written for adult readers",
        "is_romantasy_indicator": False,
    },
    # === TROPE TAGS ===
    {
        "name": "Enemies to Lovers",
        "slug": "enemies-to-lovers",
        "category": "trope",
        "description": "Characters start as enemies and fall in love",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Forced Proximity",
        "slug": "forced-proximity",
        "category": "trope",
        "description": "Characters are forced to be near each other",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Slow Burn",
        "slug": "slow-burn",
        "category": "trope",
        "description": "Romance develops gradually over time",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Friends to Lovers",
        "slug": "friends-to-lovers",
        "category": "trope",
        "description": "Friends who develop romantic feelings",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Forbidden Love",
        "slug": "forbidden-love",
        "category": "trope",
        "description": "Romance between people who shouldn't be together",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Fake Dating",
        "slug": "fake-dating",
        "category": "trope",
        "description": "Characters pretend to be in a relationship",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Marriage of Convenience",
        "slug": "marriage-of-convenience",
        "category": "trope",
        "description": "Characters marry for practical reasons",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Found Family",
        "slug": "found-family",
        "category": "trope",
        "description": "Characters form a family-like bond",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Grumpy/Sunshine",
        "slug": "grumpy-sunshine",
        "category": "trope",
        "description": "Pairing of a grumpy character with an optimistic one",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Morally Grey",
        "slug": "morally-grey",
        "category": "trope",
        "description": "Characters with ambiguous morality",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Touch Her and Die",
        "slug": "touch-her-and-die",
        "category": "trope",
        "description": "Protective love interest trope",
        "is_romantasy_indicator": True,
    },
    {
        "name": "He Falls First",
        "slug": "he-falls-first",
        "category": "trope",
        "description": "Male love interest falls in love first",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Fated Mates",
        "slug": "fated-mates",
        "category": "trope",
        "description": "Destined romantic partners",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Only One Bed",
        "slug": "only-one-bed",
        "category": "trope",
        "description": "Characters forced to share sleeping arrangements",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Who Did This to You",
        "slug": "who-did-this-to-you",
        "category": "trope",
        "description": "Protective rage when love interest is hurt",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Why Choose",
        "slug": "why-choose",
        "category": "trope",
        "description": "Protagonist has multiple love interests and doesn't choose between them",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Reverse Harem",
        "slug": "reverse-harem",
        "category": "trope",
        "description": "One protagonist with multiple romantic partners (typically female protagonist with multiple male love interests)",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Polyamory",
        "slug": "polyamory",
        "category": "trope",
        "description": "Multiple romantic relationships with consent of all involved",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Love Triangle",
        "slug": "love-triangle",
        "category": "trope",
        "description": "Protagonist torn between two love interests (typically chooses one)",
        "is_romantasy_indicator": False,
    },
    # === SETTING TAGS ===
    {
        "name": "Fae",
        "slug": "fae",
        "category": "setting",
        "description": "Features fae/faerie creatures and courts",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Dragons",
        "slug": "dragons",
        "category": "setting",
        "description": "Features dragons prominently",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Dragon Riders",
        "slug": "dragon-riders",
        "category": "setting",
        "description": "Characters who ride dragons",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Vampires",
        "slug": "vampires",
        "category": "setting",
        "description": "Features vampires",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Werewolves/Shifters",
        "slug": "shifters",
        "category": "setting",
        "description": "Features shapeshifters or werewolves",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Witches",
        "slug": "witches",
        "category": "setting",
        "description": "Features witches and witchcraft",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Magic Academy",
        "slug": "magic-academy",
        "category": "setting",
        "description": "Set in a school for magic",
        "is_romantasy_indicator": True,
    },
    {
        "name": "Royal Court",
        "slug": "royal-court",
        "category": "setting",
        "description": "Set in or around a royal court",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Medieval Setting",
        "slug": "medieval",
        "category": "setting",
        "description": "Medieval-inspired world",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Pirate",
        "slug": "pirate",
        "category": "setting",
        "description": "Features pirates or seafaring",
        "is_romantasy_indicator": False,
    },
    # === THEME TAGS ===
    {
        "name": "War/Battle",
        "slug": "war",
        "category": "theme",
        "description": "Features war or large-scale battles",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Political Intrigue",
        "slug": "political-intrigue",
        "category": "theme",
        "description": "Features political scheming and power plays",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Chosen One",
        "slug": "chosen-one",
        "category": "theme",
        "description": "Protagonist is destined for greatness",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Revenge",
        "slug": "revenge",
        "category": "theme",
        "description": "Revenge as a major plot driver",
        "is_romantasy_indicator": False,
    },
    {
        "name": "Training/Becoming Powerful",
        "slug": "training",
        "category": "theme",
        "description": "Character trains and grows in power",
        "is_romantasy_indicator": False,
    },
]

# Shelf name patterns that map to tags
SHELF_TO_TAG_MAPPING = {
    # Direct mappings
    "romantasy": "romantasy",
    "fantasy-romance": "fantasy-romance",
    "romantic-fantasy": "fantasy-romance",
    "fae": "fae",
    "faerie": "fae",
    "fairy": "fae",
    "fae-romance": "fae",
    "dragons": "dragons",
    "dragon-riders": "dragon-riders",
    "vampires": "vampires",
    "vampire": "vampires",
    "shifters": "shifters",
    "werewolves": "shifters",
    "werewolf": "shifters",
    "witches": "witches",
    "witch": "witches",
    "magic-academy": "magic-academy",
    "academy": "magic-academy",
    # Trope mappings
    "enemies-to-lovers": "enemies-to-lovers",
    "etl": "enemies-to-lovers",
    "forced-proximity": "forced-proximity",
    "slow-burn": "slow-burn",
    "slowburn": "slow-burn",
    "friends-to-lovers": "friends-to-lovers",
    "ftl": "friends-to-lovers",
    "forbidden-love": "forbidden-love",
    "fake-dating": "fake-dating",
    "found-family": "found-family",
    "grumpy-sunshine": "grumpy-sunshine",
    "morally-grey": "morally-grey",
    "morally-gray": "morally-grey",
    "fated-mates": "fated-mates",
    "mates": "fated-mates",
    # Genre mappings
    "paranormal-romance": "paranormal-romance",
    "pnr": "paranormal-romance",
    "urban-fantasy": "urban-fantasy",
    "high-fantasy": "high-fantasy",
    "dark-fantasy": "dark-fantasy",
    "ya-fantasy": "ya-fantasy",
    "adult-fantasy": "adult-fantasy",
    # Why Choose / Reverse Harem mappings
    "why-choose": "why-choose",
    "whychoose": "why-choose",
    "why-choose-romance": "why-choose",
    "reverse-harem": "reverse-harem",
    "reverseharem": "reverse-harem",
    "rh": "reverse-harem",
    "rh-romance": "reverse-harem",
    "harem": "reverse-harem",
    "polyamory": "polyamory",
    "poly": "polyamory",
    "polycule": "polyamory",
    "polyamorous": "polyamory",
    "multiple-love-interests": "why-choose",
    "multiple-mates": "why-choose",
    "shared-mate": "why-choose",
    "pack-romance": "why-choose",
    "mmf": "polyamory",
    "mfm": "polyamory",
    "love-triangle": "love-triangle",
    "lovetriangle": "love-triangle",
}


# Why Choose / Reverse Harem indicator shelves (for classification)
WHY_CHOOSE_INDICATOR_SHELVES = {
    # Strong indicators (high confidence)
    "why-choose",
    "whychoose",
    "reverse-harem",
    "reverseharem",
    "rh",
    "rh-romance",
    "harem",
}

WHY_CHOOSE_SUPPORTING_SHELVES = {
    # Supporting indicators (medium confidence)
    "poly",
    "polyamory",
    "polyamorous",
    "polycule",
    "multiple-love-interests",
    "multiple-mates",
    "shared-mate",
    "pack-romance",
    "mmf",
    "mfm",
    "mmmf",
    "fmmm",
}


def normalize_shelf_to_tag(shelf_name: str) -> str | None:
    """
    Convert a user shelf name to a standard tag slug.

    Args:
        shelf_name: The shelf name from Goodreads import

    Returns:
        Tag slug if mapping exists, None otherwise
    """
    # Normalize: lowercase, replace spaces/underscores with hyphens
    normalized = shelf_name.lower().replace(" ", "-").replace("_", "-")

    # Direct lookup
    if normalized in SHELF_TO_TAG_MAPPING:
        return SHELF_TO_TAG_MAPPING[normalized]

    # Try partial matches for common patterns
    for pattern, tag in SHELF_TO_TAG_MAPPING.items():
        if pattern in normalized:
            return tag

    return None
