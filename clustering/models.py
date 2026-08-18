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


class ClusterPrediction(models.Model):
    """
    Stores one user-submitted document clustering prediction.

    These records are kept separate from CLUSTER_DOCUMENTS so that
    prediction history does not alter the original BBC News dataset
    used to train and evaluate the K-Means model.
    """

    prediction_id = models.AutoField(
        primary_key=True,
        db_column="PREDICTION_ID",
    )

    document_text = models.TextField(
        db_column="DOCUMENT_TEXT",
    )

    predicted_cluster = models.IntegerField(
        db_column="PREDICTED_CLUSTER",
    )

    predicted_category = models.CharField(
        max_length=100,
        db_column="PREDICTED_CATEGORY",
    )

    distance_to_centroid = models.DecimalField(
        max_digits=18,
        decimal_places=10,
        db_column="DISTANCE_TO_CENTROID",
    )

    predicted_at = models.DateTimeField(
        db_column="PREDICTED_AT",
    )

    class Meta:
        managed = False
        db_table = "CLUSTER_PREDICTIONS"

        ordering = [
            "-predicted_at",
            "-prediction_id",
        ]

    def __str__(self):
        return (
            f"Prediction {self.prediction_id} "
            f"({self.predicted_category})"
        )