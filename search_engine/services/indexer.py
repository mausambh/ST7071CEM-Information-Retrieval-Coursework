"""
Preprocessing and indexing utilities for the vertical search engine.

The same text-preprocessing rules will later be applied to both
publication documents and user search queries so that they can be
compared consistently.
"""

import json
from collections import Counter
import math

from django.db import transaction
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer

from search_engine.models import (
    DocumentVector,
    InvertedIndex,
    Publication,
    TermIndex,
)

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


def build_document_text(publication):
    """
    Combine the searchable fields of one publication into a single
    document string.

    Abstract text is included when PurePortal provides it. Publications
    without an abstract can still be searched through their title,
    authors, and publication year.
    """

    parts = [
        publication.title or "",
        publication.authors or "",
        publication.abstract or "",
        str(publication.publication_year or ""),
    ]

    return " ".join(parts)


def preprocess_text(text):
    """
    Clean text before TF-IDF indexing or query processing.

    Processing steps:
    - convert text to lowercase;
    - extract alphanumeric terms;
    - remove common English stop words;
    - remove single-character tokens.

    The function intentionally uses the same rules for documents and
    user queries so their vector representations remain comparable.
    """

    if not text:
        return ""

    text = text.lower()

    # Extract words and numbers while removing punctuation and other
    # characters that do not contribute to normal keyword retrieval.
    tokens = re.findall(
        r"[a-z0-9]+",
        text,
    )

    cleaned_tokens = [
        token
        for token in tokens
        if (
            len(token) > 1
            and token not in ENGLISH_STOP_WORDS
            and (
                not token.isdigit() or (len(token) == 4 and 1900 <= int(token) <= 2099)
            )
        )
    ]

    return " ".join(cleaned_tokens)


def build_search_index(limit=None):
    """
    Build the TF-IDF search index from publications stored in Oracle.

    The indexing process:
    1. loads publication metadata from Oracle;
    2. combines title, authors, abstract, and publication year;
    3. applies the same preprocessing used for search queries;
    4. calculates TF-IDF weights;
    5. stores vocabulary IDF values in TERM_INDEX;
    6. stores document vectors in DOC_VECTORS; and
    7. stores term-to-document postings in INVERTED_INDEX.

    The optional limit argument is useful for safely testing the
    indexing process on a small number of publications.
    """

    publications = Publication.objects.all().order_by("publication_id")

    if limit is not None:
        publications = publications[:limit]

    publications = list(publications)

    if not publications:
        return {
            "documents": 0,
            "terms": 0,
            "postings": 0,
        }

    processed_documents = []

    for publication in publications:
        raw_text = build_document_text(publication)

        processed_text = preprocess_text(raw_text)

        processed_documents.append(processed_text)

    # TF-IDF converts the processed publication collection into
    # weighted numerical vectors. Each row represents one publication
    # and each column represents one term in the vocabulary.
    vectorizer = TfidfVectorizer(
        lowercase=False,
    )

    tfidf_matrix = vectorizer.fit_transform(processed_documents)

    feature_names = vectorizer.get_feature_names_out()

    indexed_at = timezone.now()

    term_records = []
    document_records = []
    posting_records = []

    # Store one IDF value for every unique vocabulary term.
    for term, idf_value in zip(
        feature_names,
        vectorizer.idf_,
    ):
        term_records.append(
            TermIndex(
                term=str(term),
                idf=float(idf_value),
            )
        )

    # Create the document vectors and inverted-index postings.
    for document_number, publication in enumerate(publications):
        row = tfidf_matrix.getrow(document_number)

        token_counts = Counter(processed_documents[document_number].split())

        vector_dictionary = {}

        for term_position, weight in zip(
            row.indices,
            row.data,
        ):
            term = str(feature_names[term_position])

            tfidf_weight = float(weight)

            vector_dictionary[term] = tfidf_weight

            posting_records.append(
                InvertedIndex(
                    term=term,
                    url=publication.publication_url,
                    term_frequency=float(token_counts[term]),
                    tf_idf=tfidf_weight,
                )
            )

        document_records.append(
            DocumentVector(
                url=publication.publication_url,
                title=publication.title,
                vector_json=json.dumps(vector_dictionary),
                indexed_at=indexed_at,
            )
        )

    # Rebuilding inside one database transaction prevents users from
    # seeing a partially rebuilt index if an error occurs.
    with transaction.atomic():
        InvertedIndex.objects.all().delete()
        DocumentVector.objects.all().delete()
        TermIndex.objects.all().delete()

        TermIndex.objects.bulk_create(
            term_records,
            batch_size=1000,
        )

        DocumentVector.objects.bulk_create(
            document_records,
            batch_size=200,
        )

        InvertedIndex.objects.bulk_create(
            posting_records,
            batch_size=1000,
        )

    return {
        "documents": len(document_records),
        "terms": len(term_records),
        "postings": len(posting_records),
    }


def search_publications(query, limit=10):
    """
    Search the indexed publication collection using TF-IDF cosine
    similarity.

    The query is preprocessed using the same rules as the documents.
    Only terms that exist in TERM_INDEX are considered.

    The inverted index is then used to retrieve only documents
    containing the query terms, rather than comparing the query with
    every publication in the collection.
    """

    processed_query = preprocess_text(query)

    query_tokens = processed_query.split()

    if not query_tokens:
        return []

    query_counts = Counter(query_tokens)

    # Retrieve IDF values only for terms that occur in the query.
    term_idfs = {
        item.term: float(item.idf)
        for item in TermIndex.objects.filter(term__in=query_counts.keys())
    }

    if not term_idfs:
        return []

    query_weights = {}

    for term, count in query_counts.items():
        if term not in term_idfs:
            continue

        query_weights[term] = float(count) * term_idfs[term]

    # Normalise the query vector so its weighting is compatible with
    # the L2-normalised vectors produced by TfidfVectorizer.
    query_length = math.sqrt(sum(weight**2 for weight in query_weights.values()))

    if query_length == 0:
        return []

    for term in query_weights:
        query_weights[term] /= query_length

    document_scores = {}

    # Use the inverted index to retrieve only postings associated
    # with query terms and accumulate the cosine similarity score.
    postings = InvertedIndex.objects.filter(term__in=query_weights.keys())

    for posting in postings:
        contribution = query_weights[posting.term] * float(posting.tf_idf)

        document_scores[posting.url] = (
            document_scores.get(
                posting.url,
                0.0,
            )
            + contribution
        )

    ranked_documents = sorted(
        document_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:limit]

    if not ranked_documents:
        return []

    urls = [url for url, score in ranked_documents]

    publications = {
        publication.publication_url: publication
        for publication in Publication.objects.filter(publication_url__in=urls)
    }

    results = []

    for rank, (url, score) in enumerate(
        ranked_documents,
        start=1,
    ):
        publication = publications.get(url)

        if publication is None:
            continue

        results.append(
            {
                "rank": rank,
                "score": float(score),
                "publication": publication,
            }
        )

    return results
