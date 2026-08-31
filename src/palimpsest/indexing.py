from collections.abc import Generator

from langchain_text_splitters import RecursiveCharacterTextSplitter

from palimpsest.embedding import Embedder


def _get_chunks(text: str) -> list[tuple[tuple, str]]:
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""],
        chunk_size=750,
        chunk_overlap=200,
        is_separator_regex=False,
        add_start_index=True,
    )
    chunks = splitter.create_documents(texts=[text])

    result = []
    for chunk in chunks:
        content = chunk.page_content
        start_offset = chunk.metadata["start_index"]
        end_offset = start_offset + len(content)
        result.append(((start_offset, end_offset), content))
    return result


def vectorize_sections(
    embedder: Embedder, accn: str, section: str, content: str
) -> Generator[tuple]:
    for idx, ((start_offset, end_offset), chunk) in enumerate(_get_chunks(content)):
        assert content[start_offset:end_offset] == chunk, (
            "Chunk doesn't correspond to offset range"
        )
        yield (
            accn,
            section,
            idx,
            start_offset,
            end_offset,
            chunk,
            embedder.embed(chunk),
        )
