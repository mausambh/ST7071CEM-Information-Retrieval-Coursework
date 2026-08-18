from collections import Counter

from django.shortcuts import render
from django.utils import timezone

from clustering.models import (
    ClusterDocument,
    ClusterPrediction,
)
from clustering.services import (
    evaluate_current_clusters,
    predict_document_cluster,
)


def clustering(request):
    """
    Display the document-clustering interface.

    The page shows the stored BBC News dataset and allows the user
    to submit a completely new document.

    A submitted document is transformed using the fitted TF-IDF
    representation and assigned to the nearest K-Means cluster.

    Every successful user prediction is also stored in the Oracle
    CLUSTER_PREDICTIONS table so that prediction history can be
    reviewed without changing the original BBC training dataset.
    """

    prediction = None
    document_text = ""

    # =========================================================
    # HANDLE NEW DOCUMENT PREDICTION
    # =========================================================

    if request.method == "POST":

        document_text = request.POST.get(
            "document_text",
            "",
        ).strip()

        if document_text:

            # Use the existing clustering service to transform the
            # submitted text and assign it to the nearest K-Means
            # centroid.
            prediction = predict_document_cluster(
                document_text
            )

            # Save the successful prediction separately from the
            # original CLUSTER_DOCUMENTS dataset.
            #
            # This ensures that user predictions do not change the
            # 150 BBC News documents used for clustering evaluation.
            ClusterPrediction.objects.create(
                document_text=document_text,
                predicted_cluster=prediction[
                    "cluster_id"
                ],
                predicted_category=prediction[
                    "category"
                ],
                distance_to_centroid=prediction[
                    "distance_to_centroid"
                ],
                predicted_at=timezone.now(),
            )

    # =========================================================
    # DATASET OVERVIEW
    # =========================================================

    # Count the original BBC News clustering documents currently
    # stored in Oracle.
    total_documents = ClusterDocument.objects.count()

    category_counts = {
        "Economics": ClusterDocument.objects.filter(
            coursework_category="Economics"
        ).count(),

        "Entertainment": ClusterDocument.objects.filter(
            coursework_category="Entertainment"
        ).count(),

        "Politics": ClusterDocument.objects.filter(
            coursework_category="Politics"
        ).count(),
    }

    # =========================================================
    # CLUSTER COMPOSITION
    # =========================================================

    cluster_composition = []

    cluster_ids = (
        ClusterDocument.objects
        .exclude(
            cluster_id__isnull=True
        )
        .values_list(
            "cluster_id",
            flat=True,
        )
        .distinct()
        .order_by(
            "cluster_id"
        )
    )

    for cluster_id in cluster_ids:

        categories = (
            ClusterDocument.objects
            .filter(
                cluster_id=cluster_id
            )
            .values_list(
                "coursework_category",
                flat=True,
            )
        )

        counts = Counter(
            categories
        )

        # The majority category provides a human-readable label
        # for the numerical K-Means cluster.
        majority_category = (
            counts.most_common(1)[0][0]
            if counts
            else "Unknown"
        )

        cluster_composition.append(
            {
                "cluster_id": cluster_id,

                "category":
                    majority_category,

                "economics":
                    counts.get(
                        "Economics",
                        0,
                    ),

                "entertainment":
                    counts.get(
                        "Entertainment",
                        0,
                    ),

                "politics":
                    counts.get(
                        "Politics",
                        0,
                    ),

                "total":
                    sum(
                        counts.values()
                    ),
            }
        )

    # =========================================================
    # CLUSTERING EVALUATION
    # =========================================================

    # Calculate the evaluation measures once after the cluster
    # composition has been constructed.
    #
    # These metrics assess both internal cluster quality and
    # agreement with the known BBC News category labels.
    evaluation = evaluate_current_clusters()

    # =========================================================
    # PREDICTION HISTORY
    # =========================================================

    # Retrieve the ten most recent user predictions.
    #
    # ClusterPrediction.Meta orders records by newest prediction
    # first, so slicing [:10] gives the latest ten submissions.
    prediction_history = (
        ClusterPrediction.objects
        .all()[:10]
    )

    prediction_history_count = (
        ClusterPrediction.objects.count()
    )

    # =========================================================
    # TEMPLATE CONTEXT
    # =========================================================

    context = {
        "total_documents":
            total_documents,

        "category_counts":
            category_counts,

        "cluster_composition":
            cluster_composition,

        "prediction":
            prediction,

        "document_text":
            document_text,

        "source_name":
            "BBC News",

        "evaluation":
            evaluation,

        "prediction_history":
            prediction_history,

        "prediction_history_count":
            prediction_history_count,
    }

    return render(
        request,
        "clustering/clustering.html",
        context,
    )