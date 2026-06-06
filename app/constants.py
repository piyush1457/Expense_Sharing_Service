# Application constants to avoid hardcoded values

SPLIT_TYPE_EQUAL = "equal"
SPLIT_TYPE_CUSTOM = "custom"

ALLOWED_SPLIT_TYPES = {SPLIT_TYPE_EQUAL, SPLIT_TYPE_CUSTOM}

# Product enhancement category list
DEFAULT_CATEGORY = "Others"
ALLOWED_CATEGORIES = {
    "Food",
    "Transport",
    "Hotel",
    "Entertainment",
    "Shopping",
    DEFAULT_CATEGORY
}
