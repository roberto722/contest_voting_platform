from hashlib import sha256


def hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
