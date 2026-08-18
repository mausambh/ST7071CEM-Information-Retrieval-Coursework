import json
import time
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from selenium import webdriver

from search_engine.models import (
    Publication,
    PublicationResearcher,
    Researcher,
)

# ============================================================
# PUREPORTAL CRAWLER CONFIGURATION
# ============================================================

BASE_URL = "https://pureportal.coventry.ac.uk"

CENTRE_URL = (
    "https://pureportal.coventry.ac.uk/en/organisations/"
    "centre-for-healthcare-and-community-transformation/"
)

CENTRE_PUBLICATIONS_URL = (
    "https://pureportal.coventry.ac.uk/en/organisations/"
    "centre-for-healthcare-and-community-transformation/publications/"
)

CENTRE_NAME = "Centre for Healthcare and Community Transformation"

ALLOWED_DOMAIN = "pureportal.coventry.ac.uk"

USER_AGENT = (
    "SoftwaricaVerticalSearchBot/1.0 " "(educational information retrieval coursework)"
)

DEFAULT_CRAWL_DELAY_SECONDS = 5

REQUEST_TIMEOUT_SECONDS = 30


# ============================================================
# ROBOTS.TXT
# ============================================================


def build_robot_parser(target_url):
    """
    Download and parse PurePortal's robots.txt.

    The crawler checks robots.txt before requesting pages so that
    the coursework crawler respects the site's crawling policy.
    """

    parsed_url = urlparse(target_url)

    robots_url = f"{parsed_url.scheme}://" f"{parsed_url.netloc}/robots.txt"

    response = requests.get(
        robots_url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    robot_parser = RobotFileParser()

    robot_parser.set_url(robots_url)

    robot_parser.parse(response.text.splitlines())

    return robot_parser


def check_crawl_permission(target_url):
    """
    Check whether robots.txt permits the requested URL.

    The function also returns the crawl delay. If PurePortal does
    not publish a delay, the coursework crawler uses a conservative
    five-second delay.
    """

    robot_parser = build_robot_parser(target_url)

    allowed = robot_parser.can_fetch(
        USER_AGENT,
        target_url,
    )

    crawl_delay = robot_parser.crawl_delay(USER_AGENT)

    if crawl_delay is None:
        crawl_delay = robot_parser.crawl_delay("*")

    if crawl_delay is None:
        crawl_delay = DEFAULT_CRAWL_DELAY_SECONDS

    return {
        "allowed": allowed,
        "crawl_delay": crawl_delay,
    }


# ============================================================
# POLITE PAGE RETRIEVAL
# ============================================================


def fetch_page(target_url):
    """
    Retrieve one PurePortal page after checking robots.txt.

    A delay is applied before every request to avoid making rapid
    requests to Coventry University's PurePortal server.
    """

    permission = check_crawl_permission(target_url)

    if not permission["allowed"]:
        raise PermissionError(f"robots.txt blocks {target_url}")

    crawl_delay = permission["crawl_delay"] or DEFAULT_CRAWL_DELAY_SECONDS

    print(
        "robots.txt allows this page. "
        f"Waiting {crawl_delay} seconds before requesting it..."
    )

    time.sleep(crawl_delay)

    response = requests.get(
        target_url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    return response


# ============================================================
# GENERAL CENTRE LINK EXTRACTION
# ============================================================


def extract_centre_links(html):
    """
    Extract links that point directly to the assigned Centre.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    centre_links = set()

    for link in soup.find_all(
        "a",
        href=True,
    ):
        href = link.get("href")

        full_url = urljoin(
            BASE_URL,
            href,
        )

        if full_url.rstrip("/") == CENTRE_URL.rstrip("/"):
            centre_links.add(full_url)

    return centre_links


# ============================================================
# CENTRE RESEARCHER EXTRACTION
# ============================================================


def extract_centre_researchers(html):
    """
    Extract researcher profile links from the Centre organisation
    page.

    Duplicate researcher profile URLs are removed.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    researchers = []

    seen_urls = set()

    # Prefer links in the organisation's persons section.
    researcher_links = soup.select(".organisation-persons " "a[href*='/en/persons/']")

    # Fallback for slightly different PurePortal page layouts.
    if not researcher_links:

        for section in soup.find_all("section"):
            section_classes = " ".join(
                section.get(
                    "class",
                    [],
                )
            ).lower()

            if (
                "organisation-person" in section_classes
                or "related-person" in section_classes
            ):
                researcher_links.extend(section.select("a[href*='/en/persons/']"))

    for link in researcher_links:

        href = link.get("href")

        if not href:
            continue

        full_url = urljoin(
            BASE_URL,
            href,
        )

        parsed_url = urlparse(full_url)

        if parsed_url.netloc != ALLOWED_DOMAIN:
            continue

        if "/en/persons/" not in parsed_url.path:
            continue

        if parsed_url.path.rstrip("/") == "/en/persons":
            continue

        clean_url = (
            f"{parsed_url.scheme}://" f"{parsed_url.netloc}" f"{parsed_url.path}"
        )

        if clean_url in seen_urls:
            continue

        seen_urls.add(clean_url)

        name = link.get_text(
            " ",
            strip=True,
        )

        researchers.append(
            {
                "name": name,
                "profile_url": clean_url,
            }
        )

    return researchers


def extract_researcher_details(
    html,
    profile_url,
):
    """
    Extract researcher details from a PurePortal person page and
    verify association with the assigned Centre.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    name = None

    heading = soup.find("h1")

    if heading:
        name = heading.get_text(
            " ",
            strip=True,
        )

    belongs_to_target_centre = False

    for link in soup.find_all(
        "a",
        href=True,
    ):
        full_url = urljoin(
            BASE_URL,
            link.get("href"),
        )

        if full_url.rstrip("/") == CENTRE_URL.rstrip("/"):
            belongs_to_target_centre = True
            break

    return {
        "name": name,
        "profile_url": profile_url,
        "centre_name": CENTRE_NAME,
        "belongs_to_target_centre": belongs_to_target_centre,
    }


# ============================================================
# RESEARCHER DATABASE STORAGE
# ============================================================


def save_researcher(details):
    """
    Create or update a verified Centre researcher in Oracle.

    PurePortal profile URL is used as the persistent identifier.
    """

    researcher, created = Researcher.objects.update_or_create(
        profile_url=details["profile_url"],
        defaults={
            "name": details["name"],
            "centre_name": CENTRE_NAME,
            "crawled_at": timezone.now(),
        },
    )

    return researcher, created


def crawl_and_save_centre_researchers():
    """
    Crawl the Centre organisation page and save verified Centre
    researcher profiles in Oracle.
    """

    print("\n==============================================")
    print("CRAWLING CENTRE RESEARCHERS")
    print("==============================================")

    response = fetch_page(CENTRE_URL)

    researcher_links = extract_centre_researchers(response.text)

    print(
        "Researcher profile links discovered:",
        len(researcher_links),
    )

    saved_researchers = []

    for position, researcher_data in enumerate(
        researcher_links,
        start=1,
    ):
        profile_url = researcher_data["profile_url"]

        print(f"\n[{position}/" f"{len(researcher_links)}]")

        print(profile_url)

        try:

            profile_response = fetch_page(profile_url)

            details = extract_researcher_details(
                profile_response.text,
                profile_url,
            )

            if not details["belongs_to_target_centre"]:
                print(
                    "[SKIPPED] " "Profile does not verify " "target Centre membership."
                )

                continue

            researcher, created = save_researcher(details)

            saved_researchers.append(researcher)

            status = "CREATED" if created else "UPDATED"

            print(f"[{status}] " f"{researcher.name}")

        except Exception as error:

            print(
                "[ERROR]",
                profile_url,
                "|",
                type(error).__name__,
                "|",
                str(error),
            )

    print(
        "\nVerified Centre researchers saved:",
        len(saved_researchers),
    )

    return saved_researchers


# ============================================================
# OFFICIAL CENTRE PUBLICATION LISTING DISCOVERY
# ============================================================


def discover_publication_urls_from_centre_listing():
    """
    Discover every research-output URL from the official Centre
    PurePortal listing.

    PurePortal protects the organisation publication listing with
    Cloudflare.

    The user first opens a normal Chrome session and completes the
    standard Cloudflare verification. Selenium then attaches to the
    already-approved browser through Chrome remote debugging.

    Important:
    - No expected publication count is hard-coded.
    - Pagination is discovered dynamically.
    - Sorting variants of the same page are normalised.
    - No CAPTCHA solver is used.
    - No stealth browser is used.
    - No proxy rotation is used.
    - No external publication source is used.
    """

    print("\n==============================================")
    print("PUREPORTAL CENTRE LISTING DISCOVERY")
    print("==============================================")

    # --------------------------------------------------------
    # ROBOTS.TXT CHECK
    # --------------------------------------------------------

    permission = check_crawl_permission(CENTRE_PUBLICATIONS_URL)

    print(
        "robots.txt allowed:",
        permission["allowed"],
    )

    print(
        "Crawl delay:",
        permission["crawl_delay"],
    )

    if not permission["allowed"]:
        raise PermissionError(
            "robots.txt does not permit the Centre " "publication listing."
        )

    crawl_delay = permission["crawl_delay"] or DEFAULT_CRAWL_DELAY_SECONDS

    # --------------------------------------------------------
    # ATTACH TO APPROVED CHROME SESSION
    # --------------------------------------------------------

    options = webdriver.ChromeOptions()

    options.debugger_address = "127.0.0.1:9222"

    try:

        driver = webdriver.Chrome(options=options)

        # Avoid an indefinite browser navigation.
        driver.set_page_load_timeout(30)

    except Exception as error:

        raise RuntimeError(
            "Could not attach to Chrome on port 9222. "
            "Start Chrome using remote debugging, open the "
            "Centre publication page manually, and wait until "
            "the normal PurePortal listing is visible."
        ) from error

    print("Attached to approved Chrome session.")

    # --------------------------------------------------------
    # DYNAMIC PAGINATION
    # --------------------------------------------------------

    pages_to_visit = [CENTRE_PUBLICATIONS_URL]

    queued_pages = {CENTRE_PUBLICATIONS_URL}

    visited_pages = set()

    publication_urls = set()

    target_listing_path = urlparse(CENTRE_PUBLICATIONS_URL).path.rstrip("/")

    while pages_to_visit:

        page_url = pages_to_visit.pop(0)

        queued_pages.discard(page_url)

        if page_url in visited_pages:
            continue

        print("\n----------------------------------------------")

        print("Opening listing page:")

        print(page_url)

        # Respect the PurePortal crawl delay.
        time.sleep(crawl_delay)

        try:

            driver.get(page_url)

        except Exception as error:

            raise RuntimeError(f"Could not load listing page: {page_url}") from error

        # Allow page content to finish rendering.
        time.sleep(2)

        page_title = driver.title or ""

        page_source = driver.page_source or ""

        # ----------------------------------------------------
        # CLOUDFLARE CHECK
        # ----------------------------------------------------

        if "just a moment" in page_title.lower() or "cf-chl-" in page_source.lower():
            raise RuntimeError(
                "Cloudflare verification is visible. "
                "Complete it manually in the attached Chrome "
                "window and then run discovery again."
            )

        visited_pages.add(page_url)

        # Parse rendered HTML locally instead of repeatedly
        # requesting element attributes through WebDriver.
        soup = BeautifulSoup(
            page_source,
            "html.parser",
        )

        new_publications_on_page = 0

        # ----------------------------------------------------
        # EXTRACT PUBLICATION DETAIL URLS
        # ----------------------------------------------------

        for link in soup.find_all(
            "a",
            href=True,
        ):

            href = link.get("href")

            if not href:
                continue

            full_url = urljoin(
                BASE_URL,
                href,
            )

            parsed_href = urlparse(full_url)

            # Stay strictly within Coventry PurePortal.
            if parsed_href.netloc != ALLOWED_DOMAIN:
                continue

            # Individual research outputs use:
            # /en/publications/<slug>/
            if "/en/publications/" not in parsed_href.path:
                continue

            # Exclude the generic publication index.
            if parsed_href.path.rstrip("/") == "/en/publications":
                continue

            clean_publication_url = (
                f"{parsed_href.scheme}://" f"{parsed_href.netloc}" f"{parsed_href.path}"
            )

            if clean_publication_url not in publication_urls:
                publication_urls.add(clean_publication_url)

                new_publications_on_page += 1

        print(
            "New publication URLs on page:",
            new_publications_on_page,
        )

        print(
            "Unique publication URLs discovered so far:",
            len(publication_urls),
        )

        # ----------------------------------------------------
        # DISCOVER PAGINATION LINKS
        # ----------------------------------------------------

        page_numbers_found = set()

        for link in soup.find_all(
            "a",
            href=True,
        ):

            href = link.get("href")

            if not href:
                continue

            full_url = urljoin(
                BASE_URL,
                href,
            )

            parsed_href = urlparse(full_url)

            if parsed_href.netloc != ALLOWED_DOMAIN:
                continue

            # Pagination must remain on this Centre's exact
            # research-output listing path.
            if parsed_href.path.rstrip("/") != target_listing_path:
                continue

            query_parameters = parse_qs(parsed_href.query)

            page_values = query_parameters.get(
                "page",
                [],
            )

            if not page_values:
                continue

            page_number = page_values[0]

            if not page_number.isdigit():
                continue

            page_numbers_found.add(int(page_number))

        # ----------------------------------------------------
        # NORMALISE PAGINATION
        # ----------------------------------------------------

        for page_number in sorted(page_numbers_found):

            # PurePortal uses page=0 for the first page.
            if page_number == 0:

                candidate_page = CENTRE_PUBLICATIONS_URL

            else:

                candidate_page = f"{CENTRE_PUBLICATIONS_URL}" f"?page={page_number}"

            # Sorting URLs such as:
            #
            # ?ordering=title&descending=false&page=1
            #
            # become:
            #
            # ?page=1
            #
            # This prevents equivalent pages being queued
            # repeatedly.

            if (
                candidate_page not in visited_pages
                and candidate_page not in queued_pages
            ):

                pages_to_visit.append(candidate_page)

                queued_pages.add(candidate_page)

                print(
                    "Pagination page discovered:",
                    candidate_page,
                )

    ordered_urls = sorted(publication_urls)

    print("\n==============================================")
    print("CENTRE LISTING DISCOVERY SUMMARY")
    print("==============================================")

    print(
        "Listing pages visited:",
        len(visited_pages),
    )

    print(
        "Unique PurePortal research outputs discovered:",
        len(ordered_urls),
    )

    return ordered_urls


# ============================================================
# LEGACY / SECONDARY RESEARCHER-PROFILE DISCOVERY
# ============================================================


def discover_publication_urls_from_researchers():
    """
    Secondary publication-discovery mechanism.

    This function is retained for reference and supporting crawler
    functionality, but the main Task 1 crawler uses the Centre's
    official research-output listing instead.
    """

    print("\n==============================================")
    print("DISCOVERING PUBLICATIONS FROM RESEARCHERS")
    print("==============================================")

    researchers = Researcher.objects.all().order_by("researcher_id")

    researcher_count = researchers.count()

    publication_urls = set()

    for position, researcher in enumerate(
        researchers,
        start=1,
    ):

        print(f"\n[{position}/{researcher_count}] " f"{researcher.name}")

        try:

            response = fetch_page(researcher.profile_url)

            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            before_count = len(publication_urls)

            for link in soup.find_all(
                "a",
                href=True,
            ):

                href = link.get("href")

                full_url = urljoin(
                    BASE_URL,
                    href,
                )

                parsed_url = urlparse(full_url)

                if parsed_url.netloc != ALLOWED_DOMAIN:
                    continue

                if "/en/publications/" not in parsed_url.path:
                    continue

                if parsed_url.path.rstrip("/") == "/en/publications":
                    continue

                clean_url = (
                    f"{parsed_url.scheme}://"
                    f"{parsed_url.netloc}"
                    f"{parsed_url.path}"
                )

                publication_urls.add(clean_url)

            new_count = len(publication_urls) - before_count

            print(
                "New publication URLs discovered:",
                new_count,
            )

        except Exception as error:

            print(
                "[ERROR]",
                researcher.profile_url,
                "|",
                type(error).__name__,
                "|",
                str(error),
            )

    ordered_urls = sorted(publication_urls)

    print(
        "\nUnique publication URLs discovered:",
        len(ordered_urls),
    )

    return ordered_urls


# ============================================================
# PUBLICATION DATE FORMATTING
# ============================================================


def format_publication_date(raw_date):
    """
    Convert PurePortal citation dates into a readable value.

    Examples:
        2026/05       -> May 2026
        2026/05/05    -> 05 May 2026
        2026           -> 2026

    The crawler keeps only the precision actually supplied by
    PurePortal rather than inventing a day when one is unavailable.
    """

    if not raw_date:
        return None

    raw_date = raw_date.strip()

    if not raw_date:
        return None

    month_names = {
        "01": "January",
        "02": "February",
        "03": "March",
        "04": "April",
        "05": "May",
        "06": "June",
        "07": "July",
        "08": "August",
        "09": "September",
        "10": "October",
        "11": "November",
        "12": "December",
    }

    date_parts = raw_date.split("/")

    if len(date_parts) >= 3:

        year = date_parts[0]

        month = month_names.get(
            date_parts[1],
            date_parts[1],
        )

        day = date_parts[2].zfill(2)

        return f"{day} {month} {year}"

    if len(date_parts) == 2:

        year = date_parts[0]

        month = month_names.get(
            date_parts[1],
            date_parts[1],
        )

        return f"{month} {year}"

    return raw_date


# ============================================================
# PUBLICATION METADATA EXTRACTION
# ============================================================


def extract_publication_details(
    html,
    publication_url,
):
    """
    Extract structured metadata from one Coventry PurePortal
    research-output page.

    The function extracts:
    - title;
    - complete author list;
    - author PurePortal profile links where available;
    - publication year;
    - full available publication date;
    - abstract;
    - research-output type;
    - author institutions;
    - Centre association.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # --------------------------------------------------------
    # ABSTRACT
    # --------------------------------------------------------

    abstract = ""

    abstract_container = soup.select_one(
        ".rendering_researchoutput_abstractportal " ".textblock"
    )

    if abstract_container:

        abstract = abstract_container.get_text(
            " ",
            strip=True,
        )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title_meta = soup.find(
        "meta",
        attrs={
            "name": "citation_title",
        },
    )

    title = title_meta.get("content") if title_meta else None

    if title:
        title = title.strip()

    # --------------------------------------------------------
    # AUTHORS
    # --------------------------------------------------------

    authors = []

    for meta in soup.find_all(
        "meta",
        attrs={
            "name": "citation_author",
        },
    ):

        author_name = meta.get("content")

        if not author_name:
            continue

        author_name = author_name.strip()

        if author_name and author_name not in authors:
            authors.append(author_name)

    # --------------------------------------------------------
    # PUBLICATION DATE / YEAR
    # --------------------------------------------------------

    publication_date_meta = soup.find(
        "meta",
        attrs={
            "name": "citation_publication_date",
        },
    )

    publication_date_raw = (
        publication_date_meta.get("content") if publication_date_meta else None
    )

    publication_year = None

    if publication_date_raw:

        year_text = publication_date_raw.strip()[:4]

        if year_text.isdigit():

            publication_year = int(year_text)

    publication_date = format_publication_date(publication_date_raw)

    # --------------------------------------------------------
    # PUBLICATION / RESEARCH OUTPUT TYPE
    # --------------------------------------------------------

    publication_type = None

    type_container = soup.select_one(
        ".rendering_researchoutput_" "publicationcontenttyperendererportalng"
    )

    if type_container:

        type_text = type_container.get_text(
            " ",
            strip=True,
        )

        # Examples:
        #
        # Research output :
        # Contribution to journal › Article › peer-review
        #
        # Research output :
        # Contribution to conference › Poster › peer-review
        #
        # Research output :
        # Contribution to book/anthology › Chapter

        if ":" in type_text:

            type_text = type_text.split(
                ":",
                1,
            )[1].strip()

        type_parts = [part.strip() for part in type_text.split("›") if part.strip()]

        if len(type_parts) >= 2:

            publication_type = type_parts[1]

        elif type_parts:

            publication_type = type_parts[0]

    # --------------------------------------------------------
    # AUTHOR PROFILE LINKS
    # --------------------------------------------------------

    author_profile_links = set()

    author_profiles = []

    # PurePortal renders internal authors and their profile links
    # in the associates-persons section.
    authors_container = soup.select_one(
        ".rendering_researchoutput_" "associatespersonsclassifiedportal"
    )

    if authors_container:

        for link in authors_container.find_all(
            "a",
            href=True,
        ):

            href = link.get("href")

            full_url = urljoin(
                BASE_URL,
                href,
            )

            parsed_url = urlparse(full_url)

            if parsed_url.netloc != ALLOWED_DOMAIN:
                continue

            if "/en/persons/" not in parsed_url.path:
                continue

            if parsed_url.path.rstrip("/") == "/en/persons":
                continue

            clean_profile_url = (
                f"{parsed_url.scheme}://" f"{parsed_url.netloc}" f"{parsed_url.path}"
            )

            author_name = link.get_text(
                " ",
                strip=True,
            )

            author_profile_links.add(clean_profile_url)

            if author_name and not any(
                item["profile_url"] == clean_profile_url for item in author_profiles
            ):

                author_profiles.append(
                    {
                        "name": author_name,
                        "profile_url": clean_profile_url,
                    }
                )

    # --------------------------------------------------------
    # CITATION AUTHOR INSTITUTIONS
    # --------------------------------------------------------

    citation_author_institutions = []

    for meta in soup.find_all(
        "meta",
        attrs={
            "name": "citation_author_institution",
        },
    ):

        institution = meta.get("content")

        if not institution:
            continue

        institution = institution.strip()

        if institution and institution not in citation_author_institutions:

            citation_author_institutions.append(institution)

    # --------------------------------------------------------
    # CENTRE MEMBERSHIP CHECK
    # --------------------------------------------------------

    belongs_to_target_centre = False

    # First check for a direct Centre organisation link.
    for link in soup.find_all(
        "a",
        href=True,
    ):

        full_url = urljoin(
            BASE_URL,
            link.get("href"),
        )

        if full_url.rstrip("/") == CENTRE_URL.rstrip("/"):

            belongs_to_target_centre = True

            break

    # Also check PurePortal citation institution metadata.
    if not belongs_to_target_centre:

        for institution in citation_author_institutions:

            institution_lower = institution.lower()

            if (
                "centre for healthcare "
                "and community transformation" in institution_lower
            ):

                belongs_to_target_centre = True

                break

    return {
        "title": title,
        "authors": authors,
        "publication_year": publication_year,
        "publication_date": publication_date,
        "publication_url": publication_url,
        "abstract": abstract,
        "publication_type": publication_type,
        "author_profiles": author_profiles,
        "author_profile_links": author_profile_links,
        "citation_author_institutions": citation_author_institutions,
        "belongs_to_target_centre": belongs_to_target_centre,
    }


# ============================================================
# PUBLICATION ELIGIBILITY
# ============================================================


def publication_has_centre_author(details):
    """
    Determine whether at least one PurePortal author profile on the
    publication matches a verified Centre researcher stored in Oracle.
    """

    author_profile_links = details.get(
        "author_profile_links",
        set(),
    )

    if not author_profile_links:
        return False

    return Researcher.objects.filter(
        profile_url__in=list(author_profile_links)
    ).exists()


# ============================================================
# PUBLICATION DATABASE STORAGE
# ============================================================


def save_publication(details):
    """
    Create or update one PurePortal research output in Oracle.

    publication_url is the persistent unique identifier so repeated
    crawls refresh existing records rather than creating duplicates.
    """

    authors_text = "; ".join(
        details.get(
            "authors",
            [],
        )
    )

    author_profiles_json = json.dumps(
        details.get(
            "author_profiles",
            [],
        ),
        ensure_ascii=False,
    )

    publication, created = Publication.objects.update_or_create(
        publication_url=details["publication_url"],
        defaults={
            "title": details.get("title"),
            "authors": authors_text,
            "publication_year": details.get("publication_year"),
            "publication_date": details.get("publication_date"),
            "abstract": details.get(
                "abstract",
                "",
            ),
            "publication_type": details.get("publication_type"),
            "author_profiles_json": author_profiles_json,
            # PurePortal is the only source used for the
            # final Task 1 publication collection.
            "source_name": "Coventry PurePortal",
            "source_url": details["publication_url"],
            "crawled_at": timezone.now(),
        },
    )

    return publication, created


# ============================================================
# PUBLICATION ↔ RESEARCHER LINKS
# ============================================================


def link_publication_to_researcher(
    publication,
    researcher,
):
    """
    Create a link between one publication and one verified Centre
    researcher.
    """

    link, created = PublicationResearcher.objects.get_or_create(
        publication=publication,
        researcher=researcher,
    )

    return link, created


def link_publication_to_centre_researchers(
    publication,
    details,
):
    """
    Link a publication to every verified Centre researcher whose
    PurePortal person profile appears on the publication page.
    """

    linked_researchers = []

    author_profile_links = details.get(
        "author_profile_links",
        set(),
    )

    if not author_profile_links:
        return linked_researchers

    researchers = Researcher.objects.filter(profile_url__in=list(author_profile_links))

    for researcher in researchers:

        link_publication_to_researcher(
            publication,
            researcher,
        )

        linked_researchers.append(researcher)

    return linked_researchers


# ============================================================
# SINGLE PUBLICATION CRAWL
# ============================================================


def crawl_and_save_publication(
    publication_url,
    discovered_from_centre_listing=False,
):
    """
    Fetch, extract, validate, store and link one PurePortal
    research output.

    Publications discovered directly from the Centre's official
    listing are already verified members of the assigned collection.
    """

    response = fetch_page(publication_url)

    details = extract_publication_details(
        response.text,
        publication_url,
    )

    if not details.get("title"):

        print(
            "[SKIPPED] " "No publication title:",
            publication_url,
        )

        return None

    has_verified_centre_author = publication_has_centre_author(details)

    belongs_to_target_centre = details.get(
        "belongs_to_target_centre",
        False,
    )

    # Publications discovered directly from the Centre's official
    # Research Output listing already have authoritative collection
    # membership.
    #
    # Publications discovered through any secondary route retain
    # the additional Centre association test.

    if not discovered_from_centre_listing:

        if not (belongs_to_target_centre or has_verified_centre_author):

            print(
                "[SKIPPED] " "No verified Centre association:",
                details["title"],
            )

            return None

    publication, created = save_publication(details)

    linked_researchers = link_publication_to_centre_researchers(
        publication,
        details,
    )

    status = "CREATED" if created else "UPDATED"

    print(f"[{status}] " f"{publication.title}")

    print(
        "  Type:",
        publication.publication_type or "Unknown",
    )

    print(
        "  Publication date:",
        publication.publication_date or "Unknown",
    )

    print(
        "  Linked author profiles:",
        len(
            details.get(
                "author_profiles",
                [],
            )
        ),
    )

    print(
        "  Verified Centre researcher links:",
        len(linked_researchers),
    )

    return publication


# ============================================================
# FULL CENTRE PUBLICATION CRAWL
# ============================================================


def crawl_and_save_discovered_publications():
    """
    Main Task 1 crawler.

    Workflow:
      1. Check robots.txt.
      2. Attach to the manually approved PurePortal Chrome session.
      3. Discover Centre research-output listing pages dynamically.
      4. Extract every unique PurePortal research-output URL.
      5. Fetch each detail page politely.
      6. Extract title, authors, author profiles, date, abstract
         and research-output type.
      7. Create or update Oracle records.
      8. Link outputs to verified Centre researchers.

    No expected publication count is hard-coded.
    """

    print("\n==============================================")
    print("PUREPORTAL CENTRE PUBLICATION CRAWL")
    print("==============================================")

    publication_urls = discover_publication_urls_from_centre_listing()

    print(
        "\nPublication URLs to process:",
        len(publication_urls),
    )

    saved_count = 0

    skipped_count = 0

    error_count = 0

    for position, publication_url in enumerate(
        publication_urls,
        start=1,
    ):

        print("\n----------------------------------------------")

        print(f"Publication {position}/" f"{len(publication_urls)}")

        print(publication_url)

        try:

            publication = crawl_and_save_publication(
                publication_url,
                discovered_from_centre_listing=True,
            )

            if publication is not None:

                saved_count += 1

            else:

                skipped_count += 1

        except PermissionError as error:

            skipped_count += 1

            print(
                "[ROBOTS SKIP]",
                str(error),
            )

        except requests.HTTPError as error:

            error_count += 1

            status_code = None

            if error.response is not None:

                status_code = error.response.status_code

            print(
                "[HTTP ERROR]",
                status_code,
                "|",
                publication_url,
            )

        except Exception as error:

            error_count += 1

            print(
                "[ERROR]",
                type(error).__name__,
                "|",
                str(error),
            )

    print("\n==============================================")
    print("PUREPORTAL CRAWL SUMMARY")
    print("==============================================")

    print(
        "Discovered URLs:",
        len(publication_urls),
    )

    print(
        "Successfully saved/updated:",
        saved_count,
    )

    print(
        "Skipped:",
        skipped_count,
    )

    print(
        "Errors:",
        error_count,
    )

    print(
        "Publications currently in Oracle:",
        Publication.objects.count(),
    )

    print(
        "Verified Centre researchers:",
        Researcher.objects.count(),
    )

    return {
        "discovered": len(publication_urls),
        "saved_or_updated": saved_count,
        "skipped": skipped_count,
        "errors": error_count,
        "database_publications": Publication.objects.count(),
        "verified_researchers": Researcher.objects.count(),
    }

def refresh_saved_publications():
    """
    Refresh publication detail pages already stored in Oracle.

    This function is intended for unattended scheduled maintenance.

    Unlike the full Centre discovery crawler, it does not open the
    Centre Research Output listing and therefore does not require the
    manually approved Chrome session used for Cloudflare-protected
    discovery.

    Workflow:
      1. Read existing PurePortal publication URLs from Oracle.
      2. Politely re-fetch each publication detail page.
      3. Update publication metadata and researcher links.
      4. Preserve the existing authoritative Centre membership.
      5. Return a summary for the scheduled maintenance command.

    Full discovery of newly added or removed Centre outputs remains a
    separate operation using crawl_and_save_discovered_publications().
    """

    print("\n==============================================")
    print("PUREPORTAL SAVED PUBLICATION REFRESH")
    print("==============================================")

    # Retrieve publication URLs already stored in Oracle.
    #
    # No expected document count is hard-coded here. If the collection
    # changes after a later full discovery crawl, the scheduled refresh
    # automatically processes whatever records are currently stored.
    stored_publications = (
        Publication.objects
        .exclude(publication_url__isnull=True)
        .exclude(publication_url="")
        .order_by("publication_id")
    )

    publication_urls = []

    for publication in stored_publications:

        publication_url = publication.publication_url

        parsed_url = urlparse(publication_url)

        # Scheduled refreshes are deliberately restricted to the same
        # official Coventry PurePortal publication-detail domain used by
        # the Task 1 vertical search engine.
        if (
            parsed_url.netloc.lower() == ALLOWED_DOMAIN.lower()
            and "/en/publications/" in parsed_url.path
        ):
            publication_urls.append(publication_url)

    print(
        "Stored PurePortal publication URLs to refresh:",
        len(publication_urls),
    )

    saved_count = 0
    skipped_count = 0
    error_count = 0

    for position, publication_url in enumerate(
        publication_urls,
        start=1,
    ):

        print("\n----------------------------------------------")

        print(
            f"Refreshing publication {position}/"
            f"{len(publication_urls)}"
        )

        print(publication_url)

        try:

            # These URLs were originally discovered from the official
            # Centre Research Output listing, so their Centre membership
            # has already been established authoritatively.
            publication = crawl_and_save_publication(
                publication_url,
                discovered_from_centre_listing=True,
            )

            if publication is not None:
                saved_count += 1

            else:
                skipped_count += 1

        except PermissionError as error:

            skipped_count += 1

            print(
                "[ROBOTS SKIP]",
                str(error),
            )

        except requests.HTTPError as error:

            error_count += 1

            status_code = None

            if error.response is not None:
                status_code = error.response.status_code

            print(
                "[HTTP ERROR]",
                status_code,
                "|",
                publication_url,
            )

        except Exception as error:

            error_count += 1

            print(
                "[ERROR]",
                type(error).__name__,
                "|",
                str(error),
            )

    print("\n==============================================")
    print("SAVED PUBLICATION REFRESH SUMMARY")
    print("==============================================")

    print(
        "Stored URLs processed:",
        len(publication_urls),
    )

    print(
        "Successfully refreshed:",
        saved_count,
    )

    print(
        "Skipped:",
        skipped_count,
    )

    print(
        "Errors:",
        error_count,
    )

    print(
        "Publications currently in Oracle:",
        Publication.objects.count(),
    )

    return {
        "stored_urls": len(publication_urls),
        "saved_or_updated": saved_count,
        "skipped": skipped_count,
        "errors": error_count,
        "database_publications": Publication.objects.count(),
    }