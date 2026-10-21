# Rola pliku: Normalizacja nazwy wydawcy z metadanych strony (czysta funkcja, bez zależności od bazy).


def clean_publisher(name: str | None) -> str | None:
    """Czyści nazwy wydawców z metadanych, np. Allen_Ai → Allen Ai."""
    if not name:
        return None
    name = " ".join(name.replace("_", " ").split())[:300]
    return name[0].upper() + name[1:] if name.islower() else name
