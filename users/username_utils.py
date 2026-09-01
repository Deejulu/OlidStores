"""
Shared username-generation utility for Olid Stores.

Every new account's username follows the single canonical pattern:

    <FirstName><LastName><Year>OLID<RandomAccountID>
    e.g. SarahOkafor2026OLID7K2M

The trailing segment is a cryptographically random alphanumeric ID (via
`secrets`), NOT a sequential counter, so usernames cannot be guessed or
enumerated. The ID is also stored on the user as `account_id`.

Ambiguous characters (0/O, 1/I/L) are excluded so the ID is safe for a
human to read off the downloaded credentials file and retype.
"""
import re
import secrets
from datetime import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone


ACCOUNT_ID_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
ACCOUNT_ID_LENGTH = 4
ACCOUNT_ID_MAX_LENGTH = 16
USERNAME_MARKER = "OLID"

_ACCOUNT_ID_RE = re.compile(
    rf"^.*\d{{4}}{USERNAME_MARKER}(?P<account_id>[{ACCOUNT_ID_ALPHABET}]+)$"
)


def generate_account_id(length: int = ACCOUNT_ID_LENGTH) -> str:
    """Generate a cryptographically random alphanumeric account ID."""
    return "".join(secrets.choice(ACCOUNT_ID_ALPHABET) for _ in range(length))


def normalize_name_part(name: str) -> str:
    """Clean a name part: unicode-normalized, ASCII-only, letters only."""
    name = re.sub(r"[^a-zA-Z]", "", name)
    return name


def build_username_prefix(first_name: str, last_name: str, year: int = None) -> str:
    """Build the non-random portion of a username: name + year + 'OLID'."""
    if year is None:
        year = timezone.now().year
    first = normalize_name_part(first_name) or "User"
    last = normalize_name_part(last_name) or "Name"
    return f"{first}{last}{year}{USERNAME_MARKER}"


def extract_account_id(username: str) -> str:
    """Extract the random account ID from a canonical generated username."""
    match = _ACCOUNT_ID_RE.match(username or "")
    return match.group("account_id") if match else ""


def generate_unique_username_with_id(
    first_name: str, last_name: str, year: int = None
) -> tuple:
    """
    Generate a unique username and its random account ID.

    Format: <FirstName><LastName><Year>OLID<RandomAccountID>
    Example: Sarah Okafor, 2026 -> ("SarahOkafor2026OLID7K2M", "7K2M")

    Returns a (username, account_id) tuple.
    """
    UserModel = get_user_model()
    prefix = build_username_prefix(first_name, last_name, year)

    attempts_per_length = 100
    length = ACCOUNT_ID_LENGTH

    while length <= ACCOUNT_ID_MAX_LENGTH:
        for _attempt in range(attempts_per_length):
            account_id = generate_account_id(length)
            username = f"{prefix}{account_id}"
            if not UserModel.objects.filter(username=username).exists():
                return username, account_id
        length += 1

    raise RuntimeError(
        "Unable to generate a unique username for "
        f"prefix {prefix!r} after exhausting the random ID space."
    )


def generate_unique_username(first_name: str, last_name: str, year: int = None) -> str:
    """Generate a unique username. Returns just the username string."""
    username, _account_id = generate_unique_username_with_id(
        first_name, last_name, year
    )
    return username
