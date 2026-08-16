"""
K-Means document clustering service for Task 2.

The clustering process converts BBC News documents into TF-IDF
vectors and groups them into three clusters using K-Means.

The known coursework categories are retained only for evaluation.
They are NOT supplied to K-Means during training, so the clustering
remains unsupervised.
"""

from collections import Counter

from django.db import transaction
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    adjusted_rand_score,
    normalized_mutual_info_score,
    silhouette_score,
)

from clustering.models import ClusterDocument


def train_document_clusters():
    """
    Cluster all stored BBC documents into three topic groups.

    Processing:
    1. load document text from Oracle;
    2. create TF-IDF vectors;
    3. apply K-Means with three clusters;
    4. save each predicted cluster back to Oracle;
    5. calculate clustering evaluation measures.

    The random state makes the experiment reproducible.
    """

    documents = list(ClusterDocument.objects.all().order_by("document_id"))

    if len(documents) < 3:
        raise ValueError("At least three documents are required " "for clustering.")

    texts = [document.document_text for document in documents]

    true_categories = [document.coursework_category for document in documents]

    # Convert document text into TF-IDF feature vectors.
    # Stop-word removal reduces common English words that provide
    # little value when separating document topics.
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        min_df=2,
        max_df=0.95,
        max_features=5000,
    )

    tfidf_matrix = vectorizer.fit_transform(texts)

    # Three clusters are used because the coursework dataset contains
    # Economics, Entertainment, and Politics documents.
    kmeans = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=20,
    )

    predicted_clusters = kmeans.fit_predict(tfidf_matrix)

    # Save the cluster number assigned to every document.
    for document, cluster_id in zip(
        documents,
        predicted_clusters,
    ):
        document.cluster_id = int(cluster_id)

    with transaction.atomic():
        ClusterDocument.objects.bulk_update(
            documents,
            ["cluster_id"],
            batch_size=100,
        )

    # Silhouette score evaluates how well-separated the clusters are
    # without using the original BBC category labels.
    silhouette = silhouette_score(
        tfidf_matrix,
        predicted_clusters,
    )

    # ARI and NMI compare the discovered clusters with the known
    # categories. These labels are used only after clustering for
    # evaluation and do not influence K-Means training.
    ari = adjusted_rand_score(
        true_categories,
        predicted_clusters,
    )

    nmi = normalized_mutual_info_score(
        true_categories,
        predicted_clusters,
    )

    cluster_sizes = Counter(int(cluster_id) for cluster_id in predicted_clusters)

    return {
        "documents": len(documents),
        "features": len(vectorizer.get_feature_names_out()),
        "clusters": 3,
        "cluster_sizes": dict(sorted(cluster_sizes.items())),
        "silhouette_score": float(silhouette),
        "adjusted_rand_index": float(ari),
        "normalized_mutual_information": float(nmi),
    }


def predict_document_cluster(document_text):
    """
    Predict the most appropriate cluster for a new document.

    K-Means is trained only on the existing BBC document text.
    The original coursework categories are used afterwards only to
    give each numeric cluster a human-readable topic name.

    This means the clustering process itself remains unsupervised.
    """

    if not document_text or not document_text.strip():
        raise ValueError("Document text cannot be empty.")

    documents = list(ClusterDocument.objects.all().order_by("document_id"))

    if len(documents) < 3:
        raise ValueError("At least three stored documents are required.")

    texts = [document.document_text for document in documents]

    # Build the same TF-IDF representation used during training.
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        min_df=2,
        max_df=0.95,
        max_features=5000,
    )

    tfidf_matrix = vectorizer.fit_transform(texts)

    kmeans = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=20,
    )

    training_clusters = kmeans.fit_predict(tfidf_matrix)

    # Work out the majority coursework category represented by each
    # numeric K-Means cluster. This avoids hard-coding cluster numbers,
    # because K-Means cluster IDs have no inherent meaning.
    cluster_categories = {}

    for cluster_id in range(3):

        categories = [
            document.coursework_category
            for document, assigned_cluster in zip(
                documents,
                training_clusters,
            )
            if assigned_cluster == cluster_id
        ]

        cluster_categories[cluster_id] = Counter(categories).most_common(1)[0][0]

    # Transform the new document using exactly the same vocabulary
    # and TF-IDF representation learned from the training collection.
    new_vector = vectorizer.transform([document_text])

    predicted_cluster = int(kmeans.predict(new_vector)[0])

    predicted_category = cluster_categories[predicted_cluster]

    # Distance to the assigned centroid is useful for explaining how
    # close the new document is to its predicted cluster.
    centroid_distances = kmeans.transform(new_vector)[0]

    distance = float(centroid_distances[predicted_cluster])

    return {
        "cluster_id": predicted_cluster,
        "category": predicted_category,
        "distance_to_centroid": distance,
    }

def evaluate_current_clusters():
    """
    Evaluate the currently stored K-Means cluster assignments.

    The silhouette score measures internal cluster separation.
    Adjusted Rand Index (ARI) and Normalized Mutual Information (NMI)
    compare the discovered clusters with the original BBC topic labels.

    The original labels are used only for evaluation, not for training.
    """

    documents = list(
        ClusterDocument.objects
        .exclude(cluster_id__isnull=True)
        .order_by("document_id")
    )

    if len(documents) < 3:
        return None

    texts = [
        document.document_text
        for document in documents
    ]

    true_categories = [
        document.coursework_category
        for document in documents
    ]

    predicted_clusters = [
        document.cluster_id
        for document in documents
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        min_df=2,
        max_df=0.95,
        max_features=5000,
    )

    tfidf_matrix = vectorizer.fit_transform(
        texts
    )

    silhouette = silhouette_score(
        tfidf_matrix,
        predicted_clusters,
    )

    ari = adjusted_rand_score(
        true_categories,
        predicted_clusters,
    )

    nmi = normalized_mutual_info_score(
        true_categories,
        predicted_clusters,
    )

    return {
        "silhouette_score": float(silhouette),
        "adjusted_rand_index": float(ari),
        "normalized_mutual_information": float(nmi),
        "features": len(
            vectorizer.get_feature_names_out()
        ),
    }