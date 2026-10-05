import hashlib


def chunk_key(model_name: str, texts: list[str]) -> str:
    """Cache key: changes whenever the model or any chunk text changes."""
    digest = hashlib.sha256(model_name.encode("utf-8"))
    for text in texts:
        digest.update(b"\0")
        digest.update(text.encode("utf-8"))
    return digest.hexdigest()
