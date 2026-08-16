from collections import Counter

from django.shortcuts import render

from clustering.models import ClusterDocument
from clustering.services import (
    evaluate_current_clusters,
    predict_document_cluster,
)


def clustering(request):
    """
    Display the document-clustering interface.

    The page shows the stored BBC dataset and allows the user to enter
    a completely new document. The submitted text is transformed using
    TF-IDF and assigned to the nearest K-Means cluster.
    """

    prediction = None
    document_text = ""

    if request.method == "POST":
        document_text = request.POST.get(
            "document_text",
            "",
        ).strip()

        if document_text:
            prediction = predict_document_cluster(document_text)

    # Summarise the dataset currently stored in Oracle.
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

    # Calculate the composition of each discovered cluster.
    cluster_composition = []

    cluster_ids = (
        ClusterDocument.objects.exclude(cluster_id__isnull=True)
        .values_list(
            "cluster_id",
            flat=True,
        )
        .distinct()
        .order_by("cluster_id")
    )

    for cluster_id in cluster_ids:
        categories = ClusterDocument.objects.filter(cluster_id=cluster_id).values_list(
            "coursework_category",
            flat=True,
        )

        counts = Counter(categories)

        # The majority category gives the numerical K-Means cluster
        # a human-readable interpretation.
        majority_category = counts.most_common(1)[0][0] if counts else "Unknown"

        cluster_composition.append(
            {
                "cluster_id": cluster_id,
                "category": majority_category,
                "economics": counts.get(
                    "Economics",
                    0,
                ),
                "entertainment": counts.get(
                    "Entertainment",
                    0,
                ),
                "politics": counts.get(
                    "Politics",
                    0,
                ),
                "total": sum(counts.values()),
            }
        )
        # Calculate evaluation measures for the stored K-Means results.
        # These metrics help assess both internal cluster separation and
        # agreement with the original BBC topic categories.
        evaluation = evaluate_current_clusters()

    context = {
        "total_documents": total_documents,
        "category_counts": category_counts,
        "cluster_composition": cluster_composition,
        "prediction": prediction,
        "document_text": document_text,
        "source_name": "BBC News",
        "evaluation": evaluation,
    }

    return render(
        request,
        "clustering/clustering.html",
        context,
    )
