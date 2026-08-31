create table section_chunks (
    id bigint generated always as identity primary key,
    accession_number text not null references filings(accession_number),
    section text not null,
    chunk_index int not null,
    start_offset int not null,
    end_offset int not null,
    content text not null,
    embedding vector(${embed_dim}),
    constraint chunks_uq unique
        (accession_number, section, chunk_index)
);

create index if not exists section_chunks_embedding_idx
    on section_chunks using hnsw (embedding vector_cosine_ops);
