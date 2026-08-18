# ST7071CEM Information Retrieval Coursework

This repository contains the complete implementation of both assessed components of the **ST7071CEM Information Retrieval** coursework.

The system is implemented using Python, Django, Oracle Database, Coventry University PurePortal, TF-IDF, inverted indexing, cosine similarity, scikit-learn, and K-Means clustering.

The project provides one integrated Django web application containing:

1. **Task 1 - Vertical Search Engine**
2. **Task 2 - Document Clustering**

Oracle Database is used as the persistent datastore for both tasks.

---

# System Overview

```text
                    ST7071CEM Coursework
                            |
                 Django Web Application
                            |
               +------------+------------+
               |                         |
               v                         v
        Task 1 Search              Task 2 Clustering
               |                         |
               v                         v
      Coventry PurePortal          BBC News Dataset
               |                         |
               v                         v
        Oracle Database             Oracle Database
               |                         |
               v                         v
      TF-IDF + Inverted Index      TF-IDF + K-Means
               |                         |
               v                         v
       Cosine Ranked Search        Cluster Prediction
                                         |
                                         v
                                Prediction History
```

---

# Task 1 - Vertical Search Engine

Task 1 implements a vertical search engine restricted to the research outputs of Coventry University's:

**Centre for Healthcare and Community Transformation**

Official PurePortal Centre page:

```text
https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/
```

Official Research Output listing:

```text
https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/publications/
```

The final implementation uses **Coventry PurePortal only** as the publication source.

No external publication metadata source is used.

---

# Final Task 1 Collection

The official Centre Research Output listing currently contains:

```text
81 research outputs
```

The crawler dynamically discovers the collection rather than hard-coding the number `81`.

A verified discovery run produced:

```text
Listing pages visited: 2
Unique PurePortal research outputs discovered: 81
```

The final Oracle collection contains:

```text
Verified Centre researchers: 18
Research outputs:            81
Indexed documents:           81
Vocabulary terms:            4,240
Inverted-index postings:     10,042
```

The collection includes all research-output types currently listed by the Centre rather than restricting the crawler to journal articles.

Current research-output types include:

- Article
- Abstract
- Review article
- Chapter
- Poster
- Comment/debate
- Commissioned report
- Other report
- Conference article
- Letter
- Web publication/site

---

# Task 1 Data Collection

## Official Centre Listing Discovery

The crawler uses the official Centre Research Output listing as the authoritative source for collection membership.

The discovery process:

1. Checks `robots.txt`
2. Accesses the approved Coventry PurePortal listing
3. Detects pagination dynamically
4. Extracts research-output URLs
5. Deduplicates URLs
6. Processes each output detail page
7. Extracts structured metadata
8. Creates or updates Oracle records
9. Links outputs with verified Centre researchers where applicable

No expected publication count is hard-coded.

Therefore, if the official Centre collection changes, a future full discovery can identify the updated number of outputs automatically.

---

# PurePortal Access Handling

Coventry PurePortal uses Cloudflare protection on the complete Centre Research Output listing.

Normal automated HTTP requests to the listing can return:

```text
HTTP 403 Forbidden
```

The implementation does not use:

- CAPTCHA solvers
- stealth browser packages
- proxy rotation
- browser fingerprint spoofing
- automated Cloudflare bypass mechanisms
- external publication metadata sources

For full collection discovery, Selenium attaches to a normal Chrome browser session that has already been approved through ordinary browser access.

The approved browser can be started with remote debugging enabled:

```powershell
Start-Process "chrome.exe" -ArgumentList "--remote-debugging-port=9222","--user-data-dir=C:\temp\pureportal-chrome"
```

The official Centre Research Output listing is then opened manually in that browser and the normal Cloudflare verification is allowed to complete.

The crawler subsequently attaches to the approved Chrome session and reads the rendered official listing.

Publication detail pages are then fetched using the crawler's normal polite request mechanism.

---

# Ethical and Polite Crawling

The Task 1 crawler is designed to minimise unnecessary load on Coventry PurePortal.

It:

- reads `robots.txt`
- checks whether a URL is permitted before requesting it
- uses a descriptive educational user agent
- applies a five-second crawl delay
- restricts crawling to the Coventry PurePortal domain
- deduplicates publication URLs
- updates existing database records instead of unnecessarily creating duplicates
- does not use external publication sources
- does not attempt automated CAPTCHA solving
- does not use proxy rotation
- does not use browser stealth or fingerprint spoofing

Example runtime behaviour:

```text
robots.txt allows this page.
Waiting 5 seconds before requesting it...
```

---

# Publication Metadata

The crawler stores structured metadata for every collected research output.

The Oracle `PUBLICATIONS` table includes:

```text
PUBLICATION_ID
TITLE
AUTHORS
PUBLICATION_YEAR
PUBLICATION_DATE
PUBLICATION_URL
ABSTRACT
PUBLICATION_TYPE
AUTHOR_PROFILES_JSON
SOURCE_NAME
SOURCE_URL
CRAWLED_AT
```

---

# Publication Date

The best date precision provided by PurePortal is preserved.

Examples:

```text
May 2026
05 May 2026
July 2026
```

A day is not invented when PurePortal provides only a month and year.

---

# Publication Type

The research-output type is extracted from the PurePortal detail page.

Examples include:

```text
Article
Poster
Abstract
Chapter
Review article
```

The publication type is displayed in the Django search results.

---

# Author Profiles

When PurePortal provides an internal author profile, the author's name and profile URL are stored in:

```text
AUTHOR_PROFILES_JSON
```

The search interface therefore displays available PurePortal author profiles as clickable links.

Authors without an internal PurePortal profile remain visible as normal text.

---

# Verified Researchers

Researchers associated with the target Centre are stored in:

```text
RESEARCHERS
```

Important fields include:

```text
RESEARCHER_ID
NAME
PROFILE_URL
CENTRE_NAME
CRAWLED_AT
```

Publication-to-researcher relationships are stored separately in:

```text
PUBLICATION_RESEARCHERS
```

The relationship table uses a composite publication/researcher primary key.

The final Oracle database currently stores:

```text
18 verified Centre researchers
```

---

# Task 1 Text Processing

Searchable publication text is constructed from available publication metadata.

The preprocessing pipeline performs operations such as:

1. Lowercase conversion
2. Token extraction
3. Punctuation filtering
4. English stop-word removal
5. Removal of single-character noise
6. Numeric-noise filtering
7. Preservation of useful four-digit publication years

The same preprocessing rules are applied to user queries.

This provides a consistent representation between indexed publications and search queries.

---

# TF-IDF Index

The final Task 1 collection is represented using **TF-IDF**.

Three persistent Oracle structures support indexing and retrieval.

---

## TERM_INDEX

Stores:

```text
TERM
IDF
```

Each unique vocabulary term appears once together with its inverse-document-frequency value.

---

## DOC_VECTORS

Stores:

```text
URL
TITLE
VECTOR_JSON
INDEXED_AT
```

Each indexed PurePortal research output has a persisted sparse TF-IDF representation.

---

## INVERTED_INDEX

Stores:

```text
INDEX_ID
TERM
URL
TERM_FREQUENCY
TF_IDF
```

The inverted index allows the search engine to retrieve postings only for terms involved in the user's query instead of scanning every document for every search.

Indexes are also created on:

```text
TERM
URL
```

to improve lookup performance.

---

# Final Verified Search Index

A verified final index build produced:

```text
Documents: 81
Terms:     4,240
Postings:  10,042
```

Oracle verification:

```text
PUBLICATIONS       81
DOCUMENT_VECTORS   81
TERMS              4240
POSTINGS           10042
```

---

# Ranked Retrieval

User queries are processed using the same preprocessing rules used during indexing.

The retrieval process performs:

```text
User Query
    |
    v
Preprocessing
    |
    v
Query Term Frequencies
    |
    v
Stored IDF Values
    |
    v
Query TF-IDF Vector
    |
    v
Inverted-Index Lookup
    |
    v
TF-IDF Score Accumulation
    |
    v
Cosine Similarity
    |
    v
Descending Relevance Ranking
```

The document vectors produced by the TF-IDF vectorizer are L2-normalised.

The query vector is also L2-normalised.

Therefore, the weighted dot product between the query vector and document vectors represents cosine similarity.

---

# Example Search

Example query:

```text
mental health stress
```

The system returns the highest-ranking research outputs with information including:

- Rank
- TF-IDF cosine-similarity score
- Publication title
- Publication date
- Research-output type
- Authors
- Clickable PurePortal author profiles where available
- Abstract
- Source
- Link to the original Coventry PurePortal record

A verified query returned ten ranked results from the current 81-document collection.

---

# Django Vertical Search Interface

The Task 1 interface is available at:

```text
http://127.0.0.1:8000/search/
```

The final interface provides:

- Search form
- Ranked result cards
- Rank numbers
- TF-IDF cosine-similarity scores
- Research-output type badges
- PurePortal source badges
- Publication dates
- Authors
- Clickable PurePortal author profiles
- Abstracts
- Direct publication links
- Navigation back to the main dashboard

---

# Full Collection Discovery and Scheduled Refresh

The final implementation deliberately separates two maintenance operations.

---

## 1. Full Collection Discovery

Full discovery accesses the official Centre Research Output listing.

It is used when checking for:

- newly added research outputs
- removed research outputs
- changes to the official Centre collection
- changes in pagination

Because the official listing is Cloudflare-protected, full discovery uses the approved Chrome session described earlier.

The main full-discovery function is:

```python
crawl_and_save_discovered_publications()
```

A verified full discovery found:

```text
Listing pages visited: 2
Unique PurePortal research outputs discovered: 81
```

---

## 2. Scheduled Stored-Publication Refresh

The weekly scheduled job does not need to rediscover the protected listing.

Instead, it:

1. Reads existing PurePortal publication URLs from Oracle
2. Validates that the URLs belong to Coventry PurePortal
3. Politely re-fetches each publication detail page
4. Updates publication metadata
5. Updates researcher relationships where applicable
6. Rebuilds the complete TF-IDF index

The scheduled refresh function is:

```python
refresh_saved_publications()
```

The number of stored publications is not hard-coded.

If the collection changes after a future approved full discovery, the scheduled refresh automatically processes the new database total.

---

# Weekly Search-Index Maintenance

The Django management command is:

```powershell
python manage.py update_search_index
```

The command performs:

```text
Stage 1 - Refresh stored PurePortal publication detail pages
Stage 2 - Rebuild the TF-IDF and inverted search indexes
```

A verified unattended run produced:

```text
Stored URLs processed: 81
Successfully refreshed: 81
Skipped: 0
Errors: 0
Publications currently in Oracle: 81

Publication refresh:
{
    'stored_urls': 81,
    'saved_or_updated': 81,
    'skipped': 0,
    'errors': 0,
    'database_publications': 81
}

Stage 2: Rebuilding TF-IDF search index

Index rebuild:
{
    'documents': 81,
    'terms': 4240,
    'postings': 10042
}

Scheduled search-engine update completed successfully.

Researchers stored: 18
Publications stored: 81
```

This verifies that the stored PurePortal collection and search index can be refreshed successfully without requiring the protected listing page during the scheduled operation.

---

# Windows Task Scheduler

The repository includes:

```text
run_weekly_search_update.bat
```

The batch file runs:

```powershell
python manage.py update_search_index
```

using the coursework virtual environment.

The local coursework installation is configured through Windows Task Scheduler.

Current schedule:

```text
Task Name: ST7071CEM Weekly Search Update
Schedule:  Weekly
Day:       Sunday
Time:      7:00 PM
State:     Enabled
```

This provides a repeatable periodic refresh mechanism for the stored PurePortal documents and the TF-IDF search index.

---

# Task 2 - Document Clustering

Task 2 implements unsupervised document clustering using:

```text
TF-IDF + K-Means
```

The dataset contains documents belonging to three coursework categories:

- Economics
- Entertainment
- Politics

---

# BBC News Dataset

The source dataset is the **BBC News dataset** made available by Greene and Cunningham.

Dataset reference:

```text
https://mlg.ucd.ie/datasets/bbc.html
```

The original dataset contains multiple categories.

For this coursework, the following mapping is used:

```text
BBC Business      -> Economics
BBC Entertainment -> Entertainment
BBC Politics      -> Politics
```

A balanced reproducible sample contains:

```text
Economics:      50
Entertainment:  50
Politics:       50
------------------
Total:         150
```

Sampling uses:

```text
random_seed = 42
```

The source category and coursework category are both preserved in Oracle.

Original BBC article content remains subject to BBC copyright.

---

# Task 2 Oracle Storage

The original clustering collection is stored in:

```text
CLUSTER_DOCUMENTS
```

Important fields include:

```text
DOCUMENT_ID
DOCUMENT_TEXT
SOURCE_CATEGORY
COURSEWORK_CATEGORY
SOURCE_NAME
SOURCE_REFERENCE
CLUSTER_ID
IMPORTED_AT
```

The original 150-document dataset remains separate from interactive user predictions.

This prevents user submissions from changing the clustering dataset used for evaluation.

---

# TF-IDF Configuration for Clustering

BBC News documents are converted into TF-IDF vectors using scikit-learn.

The vectorizer configuration includes:

```text
lowercase = True
stop_words = English
min_df = 2
max_df = 0.95
max_features = 5000
```

The final fitted model contains:

```text
3,094 TF-IDF features
```

---

# K-Means Configuration

K-Means is configured with:

```text
n_clusters = 3
random_state = 42
n_init = 20
```

The three clusters are learned without giving K-Means the original BBC topic labels.

The original labels are retained only for:

- cluster evaluation
- cluster composition analysis
- assigning a human-readable majority category to each numerical cluster

---

# Final Cluster Composition

## Cluster 0 - Economics

```text
Economics:      42
Entertainment:   2
Politics:        5
Total:          49
```

---

## Cluster 1 - Politics

```text
Economics:       6
Entertainment:   2
Politics:       45
Total:          53
```

---

## Cluster 2 - Entertainment

```text
Economics:       2
Entertainment:  46
Politics:        0
Total:          48
```

Combined total:

```text
49 + 53 + 48 = 150
```

The resulting clusters show meaningful correspondence with the original BBC categories.

---

# Clustering Evaluation

The implementation calculates three evaluation metrics.

---

## Silhouette Score

```text
0.0186
```

The Silhouette Score measures internal cluster cohesion and separation without requiring the known BBC labels.

The relatively low value indicates that the sparse TF-IDF representations of the three news categories contain substantial vocabulary overlap.

---

## Adjusted Rand Index

```text
0.6902
```

The Adjusted Rand Index compares the discovered K-Means grouping with the original BBC topic labels while correcting for agreement expected by chance.

---

## Normalized Mutual Information

```text
0.6387
```

Normalized Mutual Information measures the amount of information shared between the discovered K-Means clusters and the known BBC topic categories.

Together, ARI and NMI indicate meaningful correspondence between the unsupervised clusters and the original topics even though the category labels were not supplied during K-Means training.

---

# New Document Prediction

The Django clustering interface allows a user to submit a completely new document.

The prediction workflow is:

```text
User Document
     |
     v
TF-IDF Transformation
     |
     v
Existing Feature Space
     |
     v
K-Means Prediction
     |
     v
Nearest Centroid
     |
     v
Predicted Cluster
     |
     v
Majority Topic Category
     |
     v
Save Prediction to Oracle
```

The system returns:

- Predicted cluster
- Predicted category
- Distance to centroid

---

# Example Economics Prediction

Example input:

```text
Economic growth slowed as inflation remained high and the central bank considered changes to interest rates. Investors watched financial markets closely while businesses reported weaker consumer spending and rising costs.
```

Verified result:

```text
Predicted cluster:      0
Predicted category:     Economics
Distance to centroid:   0.9904
```

---

# Example Politics Prediction

Example input:

```text
The government announced a new parliamentary bill after ministers debated public spending and national policy. Opposition parties criticised the proposal and called for further discussion before a vote in parliament.
```

Verified result:

```text
Predicted cluster:      1
Predicted category:     Politics
Distance to centroid:   1.0104
```

The centroid distance is a distance measure in the fitted TF-IDF feature space and is not a probability value.

---

# Prediction Persistence

Every successful prediction is saved automatically to Oracle.

Prediction records are stored in:

```text
CLUSTER_PREDICTIONS
```

The table contains:

```text
PREDICTION_ID
DOCUMENT_TEXT
PREDICTED_CLUSTER
PREDICTED_CATEGORY
DISTANCE_TO_CENTROID
PREDICTED_AT
```

Predictions are deliberately **not added to `CLUSTER_DOCUMENTS`**.

Therefore:

```text
Original BBC clustering documents = 150
```

remains unchanged even after users make predictions.

---

# Prediction History

The Django interface displays prediction history retrieved directly from Oracle.

The history includes:

- Date and time
- Predicted category
- Predicted cluster
- Distance to centroid
- Document preview

The ten most recent predictions are displayed.

The interface also shows the total number of saved predictions.

Newest predictions appear first.

---

# Prediction Timezone Handling

The Django project uses:

```python
TIME_ZONE = "Asia/Kathmandu"
USE_TZ = True
```

Timestamps remain timezone-aware internally.

The web interface converts stored timestamps to Kathmandu local time and displays them in a readable format such as:

```text
18 Aug 2026, 10:56 PM
```

rather than exposing raw Oracle timestamp precision such as:

```text
18-AUG-26 05.11.05.283510000 PM
```

---

# Django Clustering Interface

The Task 2 interface is available at:

```text
http://127.0.0.1:8000/clustering/
```

The final interface displays:

- Dataset source
- Total document count
- Category counts
- Silhouette Score
- Adjusted Rand Index
- Normalized Mutual Information
- TF-IDF feature count
- Discovered K-Means clusters
- Cluster composition
- New-document prediction form
- Predicted cluster
- Predicted category
- Distance to centroid
- Prediction-save confirmation
- Oracle-backed prediction history

---

# Coursework Dashboard

The main Django dashboard is available at:

```text
http://127.0.0.1:8000/
```

The dashboard retrieves system statistics dynamically from Oracle.

Current verified Task 1 state:

```text
Researchers:              18
Research outputs:         81
Indexed documents:        81
Vocabulary terms:         4,240
Inverted-index postings: 10,042
```

Current Task 2 state:

```text
Clustering documents: 150
Categories:            3
Algorithm:             K-Means
```

The dashboard provides direct navigation to both assessed coursework components.

Task 1 publication and index totals are not hard-coded into the dashboard.

---

# Oracle Database Tables

## Task 1 Tables

```text
RESEARCHERS
PUBLICATIONS
PUBLICATION_RESEARCHERS
TERM_INDEX
DOC_VECTORS
INVERTED_INDEX
```

---

## Task 2 Tables

```text
CLUSTER_DOCUMENTS
CLUSTER_PREDICTIONS
```

The complete clean-install Oracle schema is provided in:

```text
database_setup.sql
```

The corresponding Django models use:

```python
managed = False
```

because the coursework tables are managed directly in Oracle.

---

# Database Schema Summary

```text
RESEARCHERS
    |
    | many-to-many
    |
PUBLICATION_RESEARCHERS
    |
    v
PUBLICATIONS
    |
    +------------------+
    |                  |
    v                  v
DOC_VECTORS       INVERTED_INDEX
                       |
                       v
                   TERM_INDEX


CLUSTER_DOCUMENTS
        |
        v
   TF-IDF + K-Means
        |
        v
 New Document Prediction
        |
        v
CLUSTER_PREDICTIONS
```

---

# Technology Stack

The project uses:

- Python
- Django
- Oracle Database
- Oracle SQL Developer
- python-oracledb
- Requests
- BeautifulSoup
- Selenium
- scikit-learn
- TF-IDF
- Cosine similarity
- Inverted indexing
- K-Means
- HTML
- CSS
- Windows Task Scheduler

Exact Python dependency versions are stored in:

```text
requirements.txt
```

---

# Project Structure

```text
assignment/
|
+-- manage.py
+-- README.md
+-- requirements.txt
+-- database_setup.sql
+-- run_weekly_search_update.bat
+-- .env.example
|
+-- ir_coursework/
|   +-- settings.py
|   +-- urls.py
|   +-- asgi.py
|   +-- wsgi.py
|
+-- core/
|   +-- views.py
|   +-- urls.py
|   |
|   +-- templates/
|   |   +-- core/
|   |       +-- home.html
|   |
|   +-- static/
|       +-- core/
|           +-- style.css
|
+-- search_engine/
|   +-- models.py
|   +-- views.py
|   +-- urls.py
|   |
|   +-- templates/
|   |   +-- search_engine/
|   |       +-- search.html
|   |
|   +-- services/
|   |   +-- crawler.py
|   |   +-- indexer.py
|   |
|   +-- management/
|       +-- commands/
|           +-- update_search_index.py
|
+-- clustering/
    +-- models.py
    +-- views.py
    +-- urls.py
    +-- services.py
    +-- data_loader.py
    |
    +-- templates/
        +-- clustering/
            +-- clustering.html
```

Sensitive `.env` credentials are excluded from the public repository.

---

# Installation and Setup

## 1. Clone the Repository

```powershell
git clone https://github.com/mausambh/ST7071CEM-Information-Retrieval-Coursework.git
```

Enter the project directory.

---

## 2. Create a Virtual Environment

Example:

```powershell
python -m venv .venv
```

Activate the virtual environment using the appropriate command for the operating system.

---

## 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## 4. Configure Oracle Database

Create or use an Oracle user for the coursework.

The development installation uses:

```text
IR_USER
```

For a new clean Oracle schema, run:

```text
database_setup.sql
```

through Oracle SQL Developer.

Do not run the setup script against an already populated coursework schema unless the existing custom tables have first been handled appropriately.

---

## 5. Configure Environment Variables

Create:

```text
.env
```

using:

```text
.env.example
```

as the template.

Example configuration:

```env
ORACLE_USER=IR_USER
ORACLE_PASSWORD=YOUR_ORACLE_PASSWORD
ORACLE_DSN=localhost:1521/FREEPDB1
```

Real database credentials must never be committed to GitHub.

---

## 6. Create Django Framework Tables

Run:

```powershell
python manage.py migrate
```

Django's framework tables are created through migrations.

The custom coursework tables are managed separately through Oracle and `database_setup.sql`.

---

## 7. Verify the Django Project

Run:

```powershell
python manage.py check
```

Verified output:

```text
System check identified no issues (0 silenced).
```

---

## 8. Start the Django Application

Run:

```powershell
python manage.py runserver
```

Then open the following pages.

### Coursework Dashboard

```text
http://127.0.0.1:8000/
```

### Vertical Search Engine

```text
http://127.0.0.1:8000/search/
```

### Document Clustering

```text
http://127.0.0.1:8000/clustering/
```

---

# Running Task 1 Scheduled Maintenance

Run manually with:

```powershell
python manage.py update_search_index
```

or execute:

```text
run_weekly_search_update.bat
```

The scheduled command:

1. Reads the stored PurePortal publication URLs from Oracle
2. Refreshes the publication detail pages
3. Updates stored publication information
4. Rebuilds the TF-IDF index
5. Rebuilds the inverted index

Full official Centre-listing discovery remains a separate approved-browser operation.

---

# Reproducibility

Task 2 uses fixed random values to make the experiment reproducible.

BBC sampling:

```text
random_seed = 42
```

K-Means:

```text
random_state = 42
n_init = 20
```

The clustering experiment can therefore be reproduced consistently using the same source dataset and configuration.

---

# Security

Sensitive Oracle configuration is stored in:

```text
.env
```

The `.env` file is not intended to be committed to the public repository.

A safe configuration template is provided as:

```text
.env.example
```

The Django project loads database credentials from environment variables rather than hard-coding passwords directly into the application source.

The final project does not contain unused external publication API credentials.

---

# Database Setup Script

A clean installation can create the custom Oracle coursework tables using:

```text
database_setup.sql
```

The script creates:

```text
RESEARCHERS
PUBLICATIONS
PUBLICATION_RESEARCHERS
TERM_INDEX
DOC_VECTORS
INVERTED_INDEX
CLUSTER_DOCUMENTS
CLUSTER_PREDICTIONS
```

It also creates useful database indexes and includes optional verification queries.

The script should not be executed against the already populated development schema because the tables already exist there.

---

# Final Verified System State

```text
============================================================
ST7071CEM FINAL SYSTEM STATE
============================================================

TASK 1 - VERTICAL SEARCH ENGINE

Verified Centre researchers:   18
Official research outputs:     81
Indexed documents:             81
Vocabulary terms:            4,240
Inverted-index postings:     10,042

Scheduled refresh test:

Stored URLs processed:         81
Successfully refreshed:        81
Skipped:                        0
Errors:                         0

Search index rebuild:

Documents:                     81
Terms:                       4,240
Postings:                   10,042


TASK 2 - DOCUMENT CLUSTERING

Documents:                    150

Economics:                     50
Entertainment:                 50
Politics:                      50

TF-IDF features:            3,094

Silhouette Score:          0.0186
Adjusted Rand Index:       0.6902
Normalized Mutual Info:    0.6387


CLUSTER COMPOSITION

Cluster 0 - Economics

Economics:                     42
Entertainment:                  2
Politics:                       5
Total:                         49


Cluster 1 - Politics

Economics:                      6
Entertainment:                  2
Politics:                      45
Total:                         53


Cluster 2 - Entertainment

Economics:                      2
Entertainment:                 46
Politics:                       0
Total:                         48


ADDITIONAL TASK 2 FUNCTIONALITY

- New-document cluster prediction
- Predicted topic category
- Distance-to-centroid calculation
- Oracle prediction persistence
- Prediction history
- Kathmandu local-time display

============================================================
```

---

# GitHub Repository

The coursework source repository is:

```text
https://github.com/mausambh/ST7071CEM-Information-Retrieval-Coursework
```

The repository contains:

- Django applications
- Oracle database setup script
- PurePortal crawler
- TF-IDF indexer
- Inverted index
- Cosine-similarity retrieval system
- BBC News data loader
- K-Means clustering implementation
- Clustering evaluation
- New-document prediction
- Oracle-backed prediction history
- Web templates
- Scheduled update command

Sensitive `.env` credentials and non-submission data files must remain excluded from version control.

---

# Coursework Use

This project was developed for educational purposes as part of the **ST7071CEM Information Retrieval** coursework.

Coventry University PurePortal metadata and BBC News content remain subject to the rights and usage conditions of their respective owners.

The implementation is intended for coursework demonstration, evaluation, research, and educational use.