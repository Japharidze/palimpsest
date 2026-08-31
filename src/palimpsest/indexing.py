from collections.abc import Generator

from palimpsest.embedding import Embedder


def _get_chunks(text: str) -> list[tuple[tuple, str]]:
    ...

def vectorize_sections(embedder: Embedder, sections: list[tuple]) -> Generator[tuple]:
    for accn, section, content in sections:
        for idx, ((start_offset, end_offset), chunk) in enumerate(_get_chunks(content)):
            embedding = embedder.embed(chunk)
            yield (accn, section, idx, start_offset, end_offset, chunk, embedding)
