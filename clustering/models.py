from django.db import models


class ClusterDocument(models.Model):
    """
    Represents one document used for the clustering coursework.

    The original source category is preserved so the final K-Means
    clusters can later be evaluated against the known topic labels.
    """

    document_id = models.AutoField(
        primary_key=True,
        db_column="DOCUMENT_ID",
    )

    document_text = models.TextField(
        db_column="DOCUMENT_TEXT",
    )

    source_category = models.CharField(
        max_length=100,
        db_column="SOURCE_CATEGORY",
    )

    coursework_category = models.CharField(
        max_length=100,
        db_column="COURSEWORK_CATEGORY",
    )

    source_name = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_column="SOURCE_NAME",
    )

    source_reference = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        db_column="SOURCE_REFERENCE",
    )

    cluster_id = models.IntegerField(
        null=True,
        blank=True,
        db_column="CLUSTER_ID",
    )

    imported_at = models.DateTimeField(
        null=True,
        blank=True,
        db_column="IMPORTED_AT",
    )

    class Meta:
        managed = False
        db_table = "CLUSTER_DOCUMENTS"

    def __str__(self):
        return f"Document {self.document_id} " f"({self.coursework_category})"
