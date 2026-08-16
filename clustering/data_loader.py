"""
Utilities for importing the BBC News document dataset used in
Task 2 of the coursework.

The original article content belongs to BBC News. The dataset was
prepared for research use by Greene and Cunningham and is commonly
used as a benchmark for document clustering experiments.

Dataset reference:
https://mlg.ucd.ie/datasets/bbc.html
"""

import random
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from clustering.models import ClusterDocument

# Location of the extracted BBC full-text dataset.
DATASET_ROOT = Path(__file__).resolve().parent / "data" / "bbc-fulltext" / "bbc"


# Map the BBC dataset categories to the categories required by
# the coursework specification.
CATEGORY_MAPPING = {
    "business": "Economics",
    "entertainment": "Entertainment",
    "politics": "Politics",
}


SOURCE_NAME = "BBC News"

SOURCE_REFERENCE = (
    "BBC News dataset (Greene & Cunningham): " "https://mlg.ucd.ie/datasets/bbc.html"
)


def import_bbc_documents(
    sample_per_category=50,
    random_seed=42,
):
    """
    Import a reproducible sample of BBC News articles into Oracle.

    Fifty documents are selected from each of the three coursework
    categories by default:

        Business      -> Economics
        Entertainment -> Entertainment
        Politics      -> Politics

    A fixed random seed makes the selection reproducible so the same
    clustering experiment can be repeated and explained in the report.

    Existing clustering documents are removed before importing the
    sample so repeated runs do not create duplicate database records.
    """

    random_generator = random.Random(random_seed)

    records = []

    for (
        source_category,
        coursework_category,
    ) in CATEGORY_MAPPING.items():

        category_folder = DATASET_ROOT / source_category

        files = sorted(category_folder.glob("*.txt"))

        if len(files) < sample_per_category:
            raise ValueError(
                f"Not enough documents in "
                f"{source_category}. "
                f"Found {len(files)}, but "
                f"{sample_per_category} were requested."
            )

        selected_files = random_generator.sample(
            files,
            sample_per_category,
        )

        for file_path in selected_files:

            # BBC text files are UTF-8. Reading them explicitly as
            # UTF-8 prevents characters such as the pound symbol from
            # being incorrectly displayed as encoding artefacts.
            document_text = file_path.read_text(encoding="utf-8").strip()

            if not document_text:
                continue

            records.append(
                ClusterDocument(
                    document_text=document_text,
                    source_category=source_category,
                    coursework_category=(coursework_category),
                    source_name=SOURCE_NAME,
                    source_reference=(SOURCE_REFERENCE),
                    cluster_id=None,
                    imported_at=timezone.now(),
                )
            )

    # Use one transaction so the clustering dataset is never left
    # partially imported if a database error occurs.
    with transaction.atomic():

        ClusterDocument.objects.all().delete()

        ClusterDocument.objects.bulk_create(
            records,
            batch_size=100,
        )

    return {
        "documents_imported": len(records),
        "economics": sum(
            1 for record in records if record.coursework_category == "Economics"
        ),
        "entertainment": sum(
            1 for record in records if record.coursework_category == "Entertainment"
        ),
        "politics": sum(
            1 for record in records if record.coursework_category == "Politics"
        ),
        "source": SOURCE_NAME,
    }
