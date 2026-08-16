from django.shortcuts import render

from search_engine.services.indexer import (
    search_publications,
)


def search(request):
    """
    Display the vertical search engine and process user queries.

    When a query is submitted, the same preprocessing and TF-IDF
    ranking logic used during testing is called through
    search_publications(). The ranked results are then passed to the
    Django template for display.
    """

    query = request.GET.get(
        "q",
        "",
    ).strip()

    results = []

    if query:
        results = search_publications(
            query,
            limit=10,
        )

    context = {
        "query": query,
        "results": results,
        "result_count": len(results),
    }

    return render(
        request,
        "search_engine/search.html",
        context,
    )
