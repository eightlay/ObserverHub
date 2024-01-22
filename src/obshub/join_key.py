import secrets
from typing import TypeAlias

from obshub.constants import JOIN_KEY_SIZE


JoinKey: TypeAlias = str


def generate_join_key() -> JoinKey:
    return secrets.token_urlsafe(JOIN_KEY_SIZE)
