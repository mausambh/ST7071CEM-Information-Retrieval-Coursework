from django.db import connection
from django.shortcuts import render

from clustering.models import ClusterDocument
from search_engine.models import (
    DocumentVector,
    InvertedIndex,
    Publication,
    Researcher,
    TermIndex,
)


def home(request):
    """
    Display the main coursework dashboard.

    The dashboard also performs a lightweight Oracle database check.
    Showing the database status in the interface makes it easier to
    demonstrate that Django is connected to the same Oracle database
    being managed through SQL Developer.
    """

    database_connected = False
    database_user = "Unavailable"
    researcher_count = 0
    publication_count = 0
    indexed_document_count = 0
    vocabulary_count = 0
    posting_count = 0
    clustering_document_count = 0

    try:
        # Query Oracle directly through Django's configured database
        # connection. Using DUAL provides a simple connection test
        # without changing any data.
        with connection.cursor() as cursor:
            cursor.execute("SELECT USER FROM dual")
            result = cursor.fetchone()

        database_user = result[0]
        database_connected = True

        # These counts come from the structured Oracle tables that
        # will later be populated by the PurePortal crawler.
        researcher_count = Researcher.objects.count()
        publication_count = Publication.objects.count()
        indexed_document_count = DocumentVector.objects.count()
        vocabulary_count = TermIndex.objects.count()
        posting_count = InvertedIndex.objects.count()
        clustering_document_count = ClusterDocument.objects.count()

    except Exception:
        # The web page should still load if Oracle is temporarily
        # unavailable, allowing the interface to report the problem
        # instead of failing completely.
        database_connected = False

    context = {
        "project_title": "Information Retrieval Coursework",
        "module_code": "ST7071CEM",
        "database_connected": database_connected,
        "database_user": database_user,
        "researcher_count": researcher_count,
        "publication_count": publication_count,
        "indexed_document_count": indexed_document_count,
        "vocabulary_count": vocabulary_count,
        "posting_count": posting_count,
        "clustering_document_count": clustering_document_count,
    }

    return render(
        request,
        "core/home.html",
        context,
    )
