"""
Django management command for refreshing the Task 1 vertical
search-engine collection and rebuilding its search index.

Usage:
    python manage.py update_search_index

The command provides one repeatable maintenance operation that can
later be scheduled to run periodically, for example once per week.
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
    crawl_and_save_centre_researchers,
    crawl_and_save_discovered_publications,
)

from search_engine.services.indexer import (
    build_search_index,
)


class Command(BaseCommand):
    """
    Refresh Centre researchers and publications, then rebuild
    the TF-IDF and inverted search indexes.
    """

    help = "Refresh Coventry PurePortal data and rebuild " "the vertical search index."

    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.MIGRATE_HEADING("Stage 1: Updating Centre researchers")
            )

            researcher_result = crawl_and_save_centre_researchers()

            self.stdout.write(f"Researcher crawl: " f"{researcher_result}")

            self.stdout.write(
                self.style.MIGRATE_HEADING("Stage 2: Updating publications")
            )

            publication_result = crawl_and_save_discovered_publications()

            self.stdout.write(f"Publication crawl: " f"{publication_result}")

            self.stdout.write(
                self.style.MIGRATE_HEADING("Stage 3: Rebuilding search index")
            )

            index_result = build_search_index()

            self.stdout.write(f"Index rebuild: {index_result}")

            self.stdout.write(
                self.style.SUCCESS("Search-engine update completed successfully.")
            )

            self.stdout.write(f"Researchers stored: " f"{Researcher.objects.count()}")

            self.stdout.write(f"Publications stored: " f"{Publication.objects.count()}")

        except Exception as error:
            raise CommandError(f"Search-engine update failed: {error}") from error
