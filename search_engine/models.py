from django.db import models


class Researcher(models.Model):
    """
    Represents a researcher who belongs to the target Coventry
    University centre.

    The actual table was created manually in Oracle, so Django
    uses this model to read and write the existing table rather
    than trying to create another one.
    """

    researcher_id = models.AutoField(
        primary_key=True,
        db_column="RESEARCHER_ID",
    )

    name = models.CharField(
        max_length=500,
        db_column="NAME",
    )

    profile_url = models.CharField(
        max_length=1000,
        unique=True,
        db_column="PROFILE_URL",
    )

    centre_name = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_column="CENTRE_NAME",
    )

    crawled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_column="CRAWLED_AT",
    )

    class Meta:
        # The table already exists in Oracle, therefore Django
        # should use it but should not try to create or delete it
        # through migrations.
        managed = False
        db_table = "RESEARCHERS"

    def __str__(self):
        return self.name


class Publication(models.Model):
    """
    Stores structured publication information collected from
    Coventry University's PurePortal.

    Keeping this information structured makes it possible to
    display authors, year and publication links clearly in the
    Django search interface.
    """

    publication_id = models.AutoField(
        primary_key=True,
        db_column="PUBLICATION_ID",
    )

    title = models.CharField(
        max_length=1000,
        db_column="TITLE",
    )

    authors = models.CharField(
        max_length=2000,
        null=True,
        blank=True,
        db_column="AUTHORS",
    )

    publication_year = models.IntegerField(
        null=True,
        blank=True,
        db_column="PUBLICATION_YEAR",
    )

    publication_date = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_column="PUBLICATION_DATE",
    )

    publication_url = models.CharField(
        max_length=1000,
        unique=True,
        db_column="PUBLICATION_URL",
    )

    abstract = models.TextField(
        null=True,
        blank=True,
        db_column="ABSTRACT",
    )
    publication_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column="PUBLICATION_TYPE",
    )

    author_profiles_json = models.TextField(
        null=True,
        blank=True,
        db_column="AUTHOR_PROFILES_JSON",
    )

    source_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column="SOURCE_NAME",
    )

    source_url = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        db_column="SOURCE_URL",
    )

    crawled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_column="CRAWLED_AT",
    )

    class Meta:
        # As with RESEARCHERS, Oracle already owns the physical
        # table. Django simply maps Python objects to its rows.
        managed = False
        db_table = "PUBLICATIONS"

    def __str__(self):
        return self.title


class PublicationResearcher(models.Model):
    """
    Links publications with researchers from the target Coventry
    University centre.

    The Oracle table uses PUBLICATION_ID and RESEARCHER_ID together
    as its primary key because one publication can be associated
    with multiple researchers and each researcher can have multiple
    publications.
    """

    # Django 5.2 can represent the same two-column primary key
    # that already exists in the Oracle relationship table.
    pk = models.CompositePrimaryKey(
        "publication",
        "researcher",
    )

    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        db_column="PUBLICATION_ID",
    )

    researcher = models.ForeignKey(
        Researcher,
        on_delete=models.CASCADE,
        db_column="RESEARCHER_ID",
    )

    class Meta:
        # Oracle already owns this physical table, so Django uses
        # the table without trying to create or modify it.
        managed = False
        db_table = "PUBLICATION_RESEARCHERS"

    def __str__(self):
        return f"{self.researcher} -> {self.publication}"


class TermIndex(models.Model):
    """
    Stores the inverse document frequency value for each unique term
    in the searchable publication collection.

    The TERM value is treated as the primary key because each indexed
    term should appear only once in the vocabulary.
    """

    term = models.CharField(
        max_length=255,
        primary_key=True,
        db_column="TERM",
    )

    idf = models.FloatField(
        db_column="IDF",
    )

    class Meta:
        managed = False
        db_table = "TERM_INDEX"

    def __str__(self):
        return self.term


class DocumentVector(models.Model):
    """
    Stores the processed vector representation of each publication.

    The publication URL is used as the logical primary key because
    every PurePortal publication URL is unique.
    """

    url = models.CharField(
        max_length=1000,
        primary_key=True,
        db_column="URL",
    )

    title = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        db_column="TITLE",
    )

    vector_json = models.TextField(
        db_column="VECTOR_JSON",
    )

    indexed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_column="INDEXED_AT",
    )

    class Meta:
        managed = False
        db_table = "DOC_VECTORS"

    def __str__(self):
        return self.title or self.url


class InvertedIndex(models.Model):
    """
    Stores the postings used by the inverted index.

    Each row connects one indexed term with one publication document
    and stores the term frequency and TF-IDF weight used for ranking.
    """

    index_id = models.AutoField(
        primary_key=True,
        db_column="INDEX_ID",
    )

    term = models.CharField(
        max_length=255,
        db_column="TERM",
    )

    url = models.CharField(
        max_length=1000,
        db_column="URL",
    )

    term_frequency = models.FloatField(
        db_column="TERM_FREQUENCY",
    )

    tf_idf = models.FloatField(
        db_column="TF_IDF",
    )

    class Meta:
        managed = False
        db_table = "INVERTED_INDEX"

    def __str__(self):
        return f"{self.term} -> {self.url}"
