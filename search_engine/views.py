import json

from django.shortcuts import render

from search_engine.services.indexer import (
    search_publications,
)


def search(request):
    """
    Display the Task 1 vertical search engine and process user queries.

    The search itself is performed by search_publications(), which
    ranks indexed PurePortal research outputs using TF-IDF cosine
    similarity.

    Before sending results to the template, this view also prepares
    each publication's author list so that authors with Coventry
    PurePortal person profiles can be displayed as clickable links.
    Authors without an available PurePortal profile remain visible as
    normal text.
    """

    # ---------------------------------------------------------
    # READ SEARCH QUERY
    # ---------------------------------------------------------

    query = request.GET.get(
        "q",
        "",
    ).strip()

    results = []

    # ---------------------------------------------------------
    # RUN TF-IDF / COSINE SEARCH
    # ---------------------------------------------------------

    if query:
        results = search_publications(
            query,
            limit=10,
        )

    # ---------------------------------------------------------
    # PREPARE AUTHOR PROFILE DATA FOR THE TEMPLATE
    # ---------------------------------------------------------

    for result in results:
        publication = result["publication"]

        # AUTHORS is stored in Oracle as:
        #
        # Natalie Bisal; Celine Brookes-Smith; Riya Patel; ...
        #
        # Convert it back into an ordered list.
        author_names = []

        if publication.authors:
            author_names = [
                name.strip() for name in publication.authors.split(";") if name.strip()
            ]

        # AUTHOR_PROFILES_JSON contains only authors for whom
        # PurePortal exposes a Coventry person-profile URL.
        #
        # Example:
        #
        # [
        #   {
        #       "name": "Celine Brookes-Smith",
        #       "profile_url": "https://pureportal..."
        #   }
        # ]
        profile_records = []

        if publication.author_profiles_json:
            try:
                profile_records = json.loads(publication.author_profiles_json)

            except (
                json.JSONDecodeError,
                TypeError,
            ):
                profile_records = []

        # Build a case-insensitive lookup:
        #
        # celine brookes-smith -> https://pureportal...
        profile_lookup = {}

        for profile in profile_records:
            name = profile.get(
                "name",
                "",
            ).strip()

            profile_url = profile.get(
                "profile_url",
                "",
            ).strip()

            if name and profile_url:
                profile_lookup[name.casefold()] = profile_url

        # Preserve the original author order while adding an
        # optional profile URL to each author.
        display_authors = []

        for author_name in author_names:
            display_authors.append(
                {
                    "name": author_name,
                    "profile_url": profile_lookup.get(author_name.casefold()),
                }
            )

        # Add template-ready author information directly to the
        # search-result dictionary.
        result["display_authors"] = display_authors

    # ---------------------------------------------------------
    # TEMPLATE CONTEXT
    # ---------------------------------------------------------

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
