"""
Django management command for scheduled maintenance of the
Task 1 vertical search engine.

Usage:
    python manage.py update_search_index

This command is designed for unattended execution, for example
through Windows Task Scheduler once per week.

It refreshes the PurePortal publication detail pages already stored
in Oracle and then rebuilds the TF-IDF and inverted indexes.

Full discovery of newly added or removed Centre research outputs is
kept as a separate approved operation because the official Centre
listing requires the manually approved browser session.
"""

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from search_engine.models import (
    Publication,
    Researcher,
)

from search_engine.services.crawler import (
    refresh_saved_publications,
)

from search_engine.services.indexer import (
    build_search_index,
)


class Command(BaseCommand):
    """
    Refresh stored PurePortal publications and rebuild the search index.

    This command deliberately avoids the Cloudflare-protected Centre
    listing page so it can run unattended from Windows Task Scheduler.
    """

    help = (
        "Refresh stored Coventry PurePortal publications "
        "and rebuild the vertical search index."
    )

    def handle(self, *args, **options):
        try:

            # ==================================================
            # STAGE 1 — REFRESH STORED PUBLICATIONS
            # ==================================================

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "Stage 1: Refreshing stored PurePortal publications"
                )
            )

            publication_result = refresh_saved_publications()

            self.stdout.write(f"Publication refresh: {publication_result}")

            # ==================================================
            # STAGE 2 — REBUILD SEARCH INDEX
            # ==================================================

            self.stdout.write(
                self.style.MIGRATE_HEADING("Stage 2: Rebuilding TF-IDF search index")
            )

            index_result = build_search_index()

            self.stdout.write(f"Index rebuild: {index_result}")

            # ==================================================
            # FINAL SUMMARY
            # ==================================================

            self.stdout.write(
                self.style.SUCCESS(
                    "Scheduled search-engine update " "completed successfully."
                )
            )

            self.stdout.write(f"Researchers stored: " f"{Researcher.objects.count()}")

            self.stdout.write(f"Publications stored: " f"{Publication.objects.count()}")

        except Exception as error:

            raise CommandError(
                f"Scheduled search-engine update failed: {error}"
            ) from error
