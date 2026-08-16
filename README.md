# ST7071CEM Information Retrieval Coursework

This project implements both assessed components of the **ST7071CEM Information Retrieval** coursework using Python, Django, Oracle Database, and scikit-learn.

The application contains:

1. **Task 1 — Vertical Search Engine**
2. **Task 2 — Document Clustering**

A Django web interface is provided for both tasks, while Oracle Database is used for persistent storage.

---

# Task 1 — Vertical Search Engine

The vertical search engine retrieves and ranks research publications associated with verified researchers from Coventry University's **Centre for Healthcare and Community Transformation**.

## Main Features

- Polite web crawler
- `robots.txt` checking
- Five-second crawl delay respected
- Researcher discovery from Coventry PurePortal
- Researcher profile extraction
- Publication URL discovery
- Publication metadata extraction
- Author extraction
- Publication year extraction
- Publication URL storage
- Researcher PurePortal profile URL storage
- Publication-to-researcher relationships
- Abstract extraction where available
- Oracle Database persistence
- Duplicate URL prevention
- Text preprocessing
- Stop-word removal
- Removal of numeric noise while preserving publication years
- TF-IDF indexing
- Vocabulary and IDF storage
- Stored TF-IDF document vectors
- Inverted index
- Ranked retrieval
- Cosine-style TF-IDF similarity
- Django search interface
- Repeatable crawler/index update command
- Weekly automated update through Windows Task Scheduler

---

## Task 1 Data Collection

The crawler first identifies researchers associated with the target Coventry University centre.

Verified researchers are stored in the Oracle `RESEARCHERS` table.

Publication pages are retained when at least one author profile matches a verified Centre researcher.

This ensures that the collection remains restricted to publications associated with researchers from the required Centre.

### Final Task 1 Dataset

- Verified researchers: **18**
- Publications: **68**
- Publication-researcher relationships: **94**
- Indexed documents: **68**
- Vocabulary terms: **3,601**
- Inverted-index postings: **8,527**

Abstracts were available for:

- Publications with abstracts: **60**
- Publications without abstracts: **8**
- Abstract coverage: **88.24%**

Publications without abstracts remain searchable using their available metadata such as title, authors, and publication year.

---

## PurePortal Crawling and Access Restrictions

The crawler follows the site's published `robots.txt` rules and respects the configured five-second crawl delay.

The Coventry PurePortal Centre page reports a larger collection of research outputs. However, some complete publication-listing endpoints return HTTP `403 Forbidden` to automated requests.

The implementation does **not attempt to bypass these access restrictions**.

Instead, publication URLs are collected from pages that are legitimately accessible to the crawler, particularly verified researcher profile pages.

Repeated publication URLs appearing on multiple researcher profiles are deduplicated before processing.

The final accessible collection used by the system contains **68 unique publication URLs**.

This limitation should be considered when interpreting collection coverage.

---

## Task 1 Text Preprocessing

Publication text is constructed from available fields including:

- Publication title
- Authors
- Abstract
- Publication year

The preprocessing process performs:

1. Lowercase conversion
2. Token extraction
3. Punctuation removal
4. English stop-word removal
5. Single-character token removal
6. Numeric-noise removal
7. Preservation of valid four-digit publication years

For example, meaningless numeric tokens are removed while useful publication years such as `2024`, `2025`, and `2026` remain searchable.

---

## TF-IDF Indexing

The collection is represented using **TF-IDF**.

Three Oracle structures support retrieval:

### `TERM_INDEX`

Stores:

- Vocabulary term
- Inverse Document Frequency (IDF)

### `DOC_VECTORS`

Stores:

- Publication URL
- Publication title
- Sparse TF-IDF vector represented as JSON
- Indexing timestamp

### `INVERTED_INDEX`

Stores:

- Term
- Publication URL
- Term frequency
- TF-IDF weight

The final index contains:

- **68 indexed publications**
- **3,601 vocabulary terms**
- **8,527 inverted-index postings**

---

## Ranked Search

User queries are processed using the same preprocessing rules applied to publication documents.

The search process performs:

1. Query preprocessing
2. Query term-frequency calculation
3. Query TF-IDF weighting
4. Inverted-index lookup
5. Document score accumulation
6. Cosine-style similarity ranking
7. Descending relevance ordering

An example query is:

```text
mental health stress
```

The system returns ranked publications together with:

- Rank
- Relevance score
- Publication title
- Authors
- Publication year
- Abstract preview
- Publication URL
- Verified Centre researcher profile links

---

## Django Search Interface

The search interface is available at:

```text
http://127.0.0.1:8000/search/
```

The user can enter a query and receive the top-ranked publications from the Oracle-backed search index.

---

## Task 1 Update Command

The complete crawler and index can be refreshed using the Django management command:

```powershell
python manage.py update_search_index
```

The command performs three stages:

```text
Stage 1 — Update Centre researchers
Stage 2 — Update discovered publications
Stage 3 — Rebuild the TF-IDF and inverted indexes
```

A successful verified run produced:

```text
Index rebuild:
Documents: 68
Terms: 3601
Postings: 8527

Researchers stored: 18
Publications stored: 68
```

---

## Weekly Automated Update

A Windows batch file is provided:

```text
run_weekly_search_update.bat
```

It executes:

```powershell
python manage.py update_search_index
```

using the coursework virtual environment.

The local coursework installation has also been configured through **Windows Task Scheduler**.

Current schedule:

```text
Task Name: ST7071CEM Weekly Search Update
Schedule Type: Weekly
Day: Sunday
Time: 7:00 PM
State: Enabled
```

This provides a repeatable mechanism for periodically refreshing the vertical search engine.

---

# Task 2 — Document Clustering

Task 2 performs unsupervised document clustering using **TF-IDF and K-Means**.

The dataset contains BBC News documents representing the three coursework categories:

- Economics
- Entertainment
- Politics

---

## BBC News Dataset

The original BBC dataset contains documents grouped into categories including:

- Business
- Entertainment
- Politics
- Sport
- Technology

For this coursework, the following mapping is used:

```text
BBC Business      → Economics
BBC Entertainment → Entertainment
BBC Politics      → Politics
```

A reproducible random sample of **50 documents from each category** is used.

Final clustering dataset:

```text
Economics:     50
Entertainment: 50
Politics:      50
-----------------
Total:        150
```

The random sampling process uses:

```text
random_seed = 42
```

This makes the dataset selection reproducible.

---

## BBC Dataset Source and Copyright

Source:

```text
BBC News
```

Dataset reference:

```text
https://mlg.ucd.ie/datasets/bbc.html
```

The benchmark dataset is associated with Greene and Cunningham's document-clustering research.

Original BBC article content remains copyright **BBC News**.

The source name and dataset reference are stored with all **150 documents** in Oracle rather than being documented only in the web interface.

---

## Oracle Storage for Task 2

BBC documents are stored in:

```text
CLUSTER_DOCUMENTS
```

Important fields include:

- `DOCUMENT_ID`
- `DOCUMENT_TEXT`
- `SOURCE_CATEGORY`
- `COURSEWORK_CATEGORY`
- `SOURCE_NAME`
- `SOURCE_REFERENCE`
- `CLUSTER_ID`
- `IMPORTED_AT`

The original BBC category is preserved separately from the mapped coursework category.

This allows the original labels to be used later for evaluation without supplying them to K-Means during training.

---

## TF-IDF Representation

BBC document text is converted into TF-IDF feature vectors using scikit-learn.

The clustering configuration includes:

```text
lowercase = True
stop_words = English
min_df = 2
max_df = 0.95
max_features = 5000
```

The final model uses:

```text
3,094 TF-IDF features
```

---

## K-Means Configuration

K-Means is configured with:

```text
n_clusters = 3
random_state = 42
n_init = 20
```

The three clusters correspond to the three document topics.

The original BBC category labels are **not supplied to K-Means during training**.

They are retained only for post-clustering evaluation.

---

## Final Cluster Composition

### Cluster 0 — Economics

```text
Economics:     42
Entertainment:  2
Politics:       5
Total:         49
```

### Cluster 1 — Politics

```text
Economics:      6
Entertainment:  2
Politics:      45
Total:         53
```

### Cluster 2 — Entertainment

```text
Economics:      2
Entertainment: 46
Politics:       0
Total:         48
```

Total documents:

```text
49 + 53 + 48 = 150
```

The discovered clusters therefore show strong correspondence with the original BBC topics.

---

## Clustering Evaluation

Three evaluation measures are calculated.

### Silhouette Score

```text
0.0186
```

The silhouette score measures internal separation and cohesion without requiring known category labels.

The relatively low value indicates substantial vocabulary overlap between the three news categories.

### Adjusted Rand Index

```text
0.6902
```

The Adjusted Rand Index compares the discovered K-Means grouping with the original BBC categories while correcting for agreement expected by chance.

### Normalized Mutual Information

```text
0.6387
```

Normalized Mutual Information measures shared information between the discovered clusters and the known document topics.

Together, ARI and NMI indicate that the unsupervised clusters correspond reasonably well with the original categories even though those labels were not used during K-Means training.

---

## New Document Prediction

The clustering interface allows a user to paste a completely new document.

The system:

1. Loads the existing BBC document collection
2. Builds the TF-IDF representation
3. Fits K-Means using the existing collection
4. Transforms the new document using the same TF-IDF vocabulary
5. Finds its nearest K-Means centroid
6. Returns the predicted cluster
7. Maps the numeric cluster to its majority topic category

Example Economics-style input:

```text
The central bank raised interest rates after inflation remained high.
Financial markets reacted to the decision while businesses warned
that higher borrowing costs could reduce investment, consumer
spending and economic growth.
```

Verified result:

```text
Predicted cluster: 0
Predicted category: Economics
Distance to centroid: 0.9840
```

---

## Django Clustering Interface

The clustering interface is available at:

```text
http://127.0.0.1:8000/clustering/
```

The page displays:

- Dataset size
- BBC attribution
- Category counts
- Clustering evaluation metrics
- Cluster composition
- New-document text input
- Predicted cluster
- Predicted topic
- Distance to centroid

---

# Django Dashboard

The main application dashboard is available at:

```text
http://127.0.0.1:8000/
```

The dashboard displays live Oracle-backed statistics for both tasks.

Current Task 1 statistics:

```text
Researchers: 18
Publications: 68
Indexed documents: 68
Vocabulary terms: 3601
Inverted-index postings: 8527
```

Current Task 2 statistics:

```text
Clustering documents: 150
```

Both assessed components are accessible directly from the dashboard.

---

# Technology Stack

The project uses:

- Python
- Django
- Oracle Database
- Oracle SQL Developer
- python-oracledb
- BeautifulSoup
- Requests
- Selenium
- scikit-learn
- TF-IDF
- K-Means
- HTML
- CSS
- Windows Task Scheduler

---

# Main Python Dependencies

Important dependency versions include:

```text
beautifulsoup4==4.15.0
Django==5.2.17
oracledb==4.0.2
python-dotenv==1.2.2
requests==2.34.2
scikit-learn==1.9.0
selenium==4.46.0
```

The complete dependency list is stored in:

```text
requirements.txt
```

---

# Project Structure

The main coursework structure is:

```text
assignment/
│
├── manage.py
├── README.md
├── requirements.txt
├── database_setup.sql
├── run_weekly_search_update.bat
├── .env
│
├── ir_coursework/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── core/
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   └── static/
│
├── search_engine/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   │   └── search_engine/
│   │       └── search.html
│   │
│   ├── services/
│   │   ├── crawler.py
│   │   └── indexer.py
│   │
│   └── management/
│       └── commands/
│           └── update_search_index.py
│
└── clustering/
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── services.py
    ├── data_loader.py
    │
    ├── templates/
    │   └── clustering/
    │       └── clustering.html
    │
    └── data/
        └── bbc-fulltext/
```

---

# Oracle Database

Oracle Database is used as the main persistent datastore.

Oracle SQL Developer is used to inspect and manage the database.

## Task 1 Tables

Custom Task 1 tables include:

```text
RESEARCHERS
PUBLICATIONS
PUBLICATION_RESEARCHERS
TERM_INDEX
DOC_VECTORS
INVERTED_INDEX
```

Existing crawler-support tables may also include:

```text
RAW_PAGES
CRAWL_LOG
```

## Task 2 Table

Task 2 uses:

```text
CLUSTER_DOCUMENTS
```

The custom table definitions required for a clean installation are provided in:

```text
database_setup.sql
```

---

# Installation and Setup

## 1. Create a Virtual Environment

Example:

```powershell
python -m venv .venv
```

Activate it using the appropriate command for the operating system.

---

## 2. Install Dependencies

From the project directory:

```powershell
pip install -r requirements.txt
```

---

## 3. Configure Oracle Database

Create or use an Oracle user for the coursework.

The implementation uses:

```text
IR_USER
```

Run:

```text
database_setup.sql
```

in Oracle SQL Developer when setting up a **new clean database**.

Do not run the setup script unnecessarily on an existing populated database because the custom tables may already exist.

---

## 4. Configure Environment Variables

Create:

```text
assignment\.env
```

Example:

```env
ORACLE_USER=IR_USER
ORACLE_PASSWORD=YOUR_ORACLE_PASSWORD
ORACLE_DSN=localhost:1521/FREEPDB1
```

Real database passwords must not be committed or included in submitted screenshots.

---

## 5. Create Django Framework Tables

Run:

```powershell
python manage.py migrate
```

This creates Django's own framework tables for components such as authentication and sessions.

The custom coursework tables are managed separately through Oracle.

---

## 6. Verify Django Configuration

Run:

```powershell
python manage.py check
```

A successful configuration should report:

```text
System check identified no issues (0 silenced).
```

---

## 7. Run the Django Application

Run:

```powershell
python manage.py runserver
```

Open the dashboard:

```text
http://127.0.0.1:8000/
```

Vertical Search Engine:

```text
http://127.0.0.1:8000/search/
```

Document Clustering:

```text
http://127.0.0.1:8000/clustering/
```

---

# Updating Task 1

To refresh Centre researchers, publications, and the search index:

```powershell
python manage.py update_search_index
```

Alternatively run:

```text
run_weekly_search_update.bat
```

The batch file is intended for use with Windows Task Scheduler.

---

# Reproducibility

Important random operations use fixed seeds.

BBC sampling:

```text
random_seed = 42
```

K-Means:

```text
random_state = 42
n_init = 20
```

This allows the main clustering experiment to be reproduced consistently.

---

# Security

Sensitive configuration is stored in:

```text
.env
```

and should not be committed to a public repository or included in submitted source files containing real credentials.

The application source code reads Oracle credentials from environment variables rather than hard-coding passwords inside Django settings.

---

# Ethical Crawling

The Task 1 crawler is designed to behave politely.

It:

- Reads `robots.txt`
- Checks permission before requesting pages
- Uses a descriptive coursework user agent
- Respects the site's five-second crawl delay
- Avoids attempts to bypass HTTP `403` restrictions
- Caches parsed `robots.txt` rules during a crawler run
- Deduplicates publication URLs
- Updates existing database records instead of unnecessarily creating duplicates

---

# Final Verified System Summary

The final implementation was verified with the following results:

```text
=== ST7071CEM FINAL SYSTEM SUMMARY ===

TASK 1 - VERTICAL SEARCH ENGINE
Researchers: 18
Publications: 68
Publication-Researcher links: 94
Indexed documents: 68
Vocabulary terms: 3601
Inverted-index postings: 8527

TASK 2 - DOCUMENT CLUSTERING
Documents: 150
Economics: 50
Entertainment: 50
Politics: 50
Silhouette Score: 0.0186
Adjusted Rand Index: 0.6902
Normalized Mutual Information: 0.6387
TF-IDF Features: 3094
```

---

# Coursework Note

This project was developed for educational purposes as part of the **ST7071CEM Information Retrieval** coursework.

External publication metadata, research content, and BBC News documents remain subject to the copyright and usage conditions of their respective original sources.

The application is intended for coursework demonstration and research/educational use.