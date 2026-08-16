import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from search_engine.models import (
    Publication,
    PublicationResearcher,
    Researcher,
)
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


# This is the organisation specified in the coursework brief.
# The crawler will eventually start here and discover the centre's
# researchers and their publications.
CENTRE_URL = (
    "https://pureportal.coventry.ac.uk/en/organisations/"
    "centre-for-healthcare-and-community-transformation/"
)

# A descriptive user agent makes the purpose of the crawler clear.
# The crawler is being developed only for this academic coursework.
USER_AGENT = (
    "ST7071CEM-VerticalSearchBot/1.0 "
    "(Information Retrieval Coursework)"
)

# Cache the parsed robots.txt rules after the first successful request.
# This avoids downloading the same robots.txt file before every page,
# reducing unnecessary requests to the PurePortal server.
_ROBOT_CACHE = {}

def build_robot_parser(target_url):
    """
    Download and parse robots.txt for the target website.

    The parsed rules are cached after the first successful request so
    repeated page requests do not unnecessarily download robots.txt
    again. This makes the coursework crawler more polite and efficient.
    """

    parsed_url = urlparse(target_url)

    site_root = (
        f"{parsed_url.scheme}://"
        f"{parsed_url.netloc}"
    )

    robots_url = (
        f"{site_root}/robots.txt"
    )

    # Reuse the previously parsed rules when this website has already
    # been checked during the current crawler run.
    if site_root in _ROBOT_CACHE:
        return (
            _ROBOT_CACHE[site_root],
            robots_url,
        )

    response = requests.get(
        robots_url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=15,
    )

    response.raise_for_status()

    robot_parser = RobotFileParser()
    robot_parser.set_url(robots_url)

    robot_parser.parse(
        response.text.splitlines()
    )

    # Store the parser so later requests to the same PurePortal domain
    # can reuse the rules without creating another HTTP request.
    _ROBOT_CACHE[site_root] = robot_parser

    return robot_parser, robots_url


def check_crawl_permission(target_url=CENTRE_URL):
    """
    Check whether the target PurePortal page may be crawled.

    The function returns useful information rather than immediately
    crawling the page. This keeps robots checking separate from the
    later page-extraction logic and makes the system easier to test.
    """

    robot_parser, robots_url = build_robot_parser(target_url)

    allowed = robot_parser.can_fetch(
        USER_AGENT,
        target_url,
    )

    # Some websites define a crawl delay for every crawler using '*'.
    # We check our own user agent first and then fall back to that rule.
    crawl_delay = robot_parser.crawl_delay(USER_AGENT)

    if crawl_delay is None:
        crawl_delay = robot_parser.crawl_delay("*")

    return {
        "target_url": target_url,
        "robots_url": robots_url,
        "allowed": allowed,
        "crawl_delay": crawl_delay,
    }

def fetch_page(target_url):
    """
    Retrieve a web page only after confirming that robots.txt allows
    access.

    The function also waits for the crawl delay specified by the
    website before requesting the page. Keeping this behaviour inside
    one function helps ensure that later crawler stages remain polite.
    """

    import time

    permission = check_crawl_permission(target_url)

    # Never request a page that robots.txt does not permit.
    if not permission["allowed"]:
        raise PermissionError(
            f"Crawling is not allowed for: {target_url}"
        )

    # Use the website's declared delay. If no delay is supplied,
    # fall back to five seconds so the coursework crawler still
    # avoids making rapid consecutive requests.
    crawl_delay = permission["crawl_delay"] or 5

    print(
        f"robots.txt allows this page. "
        f"Waiting {crawl_delay} seconds before requesting it..."
    )

    time.sleep(crawl_delay)

    response = requests.get(
        target_url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=20,
    )

    response.raise_for_status()

    return response

def extract_centre_links(html, base_url=CENTRE_URL):
    """
    Extract researcher-profile and publication links from the target
    Coventry University centre page.

    Only links belonging to PurePortal are kept. Separating researcher
    and publication URLs now will make the later crawling stages easier
    to understand, test and explain.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    publication_links = set()
    researcher_links = set()

    for link in soup.find_all("a", href=True):
        href = link.get("href")

        # Convert relative links such as /en/persons/... into complete
        # PurePortal URLs before checking what type of page they are.
        if href.startswith("/"):
            full_url = (
                "https://pureportal.coventry.ac.uk"
                + href
            )
        else:
            full_url = href

        # Publication pages use /en/publications/ in their URL.
        if (
            full_url
            and "/en/publications/" in full_url
            and full_url.rstrip("/")
            != "https://pureportal.coventry.ac.uk/en/publications"
        ):
            publication_links.add(full_url)

        # Researcher profile pages use /en/persons/ in their URL.
        elif (
            full_url
            and "/en/persons/" in full_url
            and full_url.rstrip("/")
            != "https://pureportal.coventry.ac.uk/en/persons"
            ):
                researcher_links.add(full_url)

    return {
        "publication_links": sorted(publication_links),
        "researcher_links": sorted(researcher_links),
    }

def extract_researcher_details(html, profile_url):
    """
    Extract the researcher's name and publication links from an
    individual Coventry PurePortal profile page.

    The researcher's name is taken from the page's main H1 heading.
    Publication URLs are collected separately so they can later be
    crawled and stored in the PUBLICATIONS table.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # PurePortal displays the researcher's name in the main H1
    # heading of an individual profile page.
    heading = soup.find("h1")

    researcher_name = (
        heading.get_text(" ", strip=True)
        if heading
        else None
    )

    publication_links = set()

    for link in soup.find_all("a", href=True):
        href = link.get("href")

        if href.startswith("/"):
            full_url = (
                "https://pureportal.coventry.ac.uk"
                + href
            )
        else:
            full_url = href

        # Ignore the general publications directory and keep only
        # links that point to individual publication records.
        if (
            full_url
            and "/en/publications/" in full_url
            and full_url.rstrip("/")
            != "https://pureportal.coventry.ac.uk/en/publications"
        ):
            publication_links.add(full_url)

    return {
        "name": researcher_name,
        "profile_url": profile_url,
        "publication_links": sorted(publication_links),
    }

def extract_publication_details(html, publication_url):
    """
    Extract structured publication information from an individual
    Coventry PurePortal publication page.

    PurePortal provides citation metadata intended for scholarly
    indexing systems. Using these fields is more reliable than trying
    to infer titles, authors and dates from the visual page layout.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

        # Extract only the publication's abstract text.
    # PurePortal places the abstract inside a dedicated
    # rendering_researchoutput_abstractportal container.
    abstract = ""

    abstract_container = soup.select_one(
        ".rendering_researchoutput_abstractportal .textblock"
    )

    if abstract_container:
        abstract = abstract_container.get_text(
            " ",
            strip=True,
        )

    # ---------------------------------------------------------
    # TITLE
    # ---------------------------------------------------------

    title_meta = soup.find(
        "meta",
        attrs={"name": "citation_title"},
    )

    title = (
        title_meta.get("content")
        if title_meta
        else None
    )

    # ---------------------------------------------------------
    # AUTHORS
    # ---------------------------------------------------------

    # A publication can contain several citation_author tags.
    # Keeping all of them preserves the complete authorship list.
    authors = [
        meta.get("content")
        for meta in soup.find_all(
            "meta",
            attrs={"name": "citation_author"},
        )
        if meta.get("content")
    ]

    # ---------------------------------------------------------
    # PUBLICATION DATE / YEAR
    # ---------------------------------------------------------

    publication_date_meta = soup.find(
        "meta",
        attrs={"name": "citation_publication_date"},
    )

    publication_date = (
        publication_date_meta.get("content")
        if publication_date_meta
        else None
    )

    publication_year = None

    if publication_date:
        # PurePortal currently returns dates in forms such as
        # 2026/05, so the first four characters provide the year.
        year_text = publication_date[:4]

        if year_text.isdigit():
            publication_year = int(year_text)

    # ---------------------------------------------------------
    # AUTHOR PROFILE LINKS
    # ---------------------------------------------------------

    author_profile_links = set()

    for link in soup.find_all("a", href=True):
        href = link.get("href")

        if href.startswith("/"):
            full_url = (
                "https://pureportal.coventry.ac.uk"
                + href
            )
        else:
            full_url = href

        if (
            full_url
            and "/en/persons/" in full_url
            and full_url.rstrip("/")
            != "https://pureportal.coventry.ac.uk/en/persons"
        ):
            author_profile_links.add(full_url)

    # ---------------------------------------------------------
    # CENTRE MEMBERSHIP CHECK
    # ---------------------------------------------------------

    centre_url = (
        "https://pureportal.coventry.ac.uk/en/organisations/"
        "centre-for-healthcare-and-community-transformation/"
    )

    belongs_to_target_centre = False

    for link in soup.find_all("a", href=True):
        href = link.get("href")

        if href.startswith("/"):
            full_url = (
                "https://pureportal.coventry.ac.uk"
                + href
            )
        else:
            full_url = href

        if (
            full_url
            and full_url.rstrip("/")
            == centre_url.rstrip("/")
        ):
            belongs_to_target_centre = True
            break

    return {
        "title": title,
        "authors": authors,
        "publication_year": publication_year,
        "publication_url": publication_url,
        "abstract": abstract,
        "author_profile_links": author_profile_links,
        "belongs_to_target_centre": belongs_to_target_centre,
    }

def save_publication(details):
    """
    Save parsed publication metadata into the Oracle PUBLICATIONS table.

    Eligibility for the vertical search engine is checked before this
    function is called. This function is responsible only for creating
    or updating the database record.

    update_or_create() uses the publication URL as the unique key so
    repeated weekly crawls update existing records instead of creating
    duplicates.
    """

    authors_text = "; ".join(
        details["authors"]
    )

    publication, created = (
        Publication.objects.update_or_create(
            publication_url=details[
                "publication_url"
            ],
            defaults={
                "title": details["title"],
                "authors": authors_text,
                "publication_year": details[
                "publication_year"
                ],
                "abstract": details.get(
            "abstract",
            "",
            ),
            "crawled_at": timezone.now(),
            },
        )
    )

    return publication, created

def save_researcher(details):
    """
    Save a researcher from the target Coventry University centre
    into the Oracle RESEARCHERS table.

    The profile URL is unique, so update_or_create() prevents
    duplicate researcher records when the crawler runs again.
    """

    # A researcher record is only useful if both the person's name
    # and their PurePortal profile URL were successfully extracted.
    if not details["name"] or not details["profile_url"]:
        return None, False

    researcher, created = Researcher.objects.update_or_create(
        profile_url=details["profile_url"],
        defaults={
            "name": details["name"],
            "centre_name": (
                "Centre for Healthcare and Community Transformation"
            ),
            "crawled_at": timezone.now(),
        },
    )

    return researcher, created

def link_publication_to_researcher(publication, researcher):
    """
    Create the relationship between a publication and a researcher.

    The relationship table is necessary because one publication may
    contain several Centre researchers, while each researcher may also
    contribute to many different publications.
    """

    relationship, created = (
        PublicationResearcher.objects.get_or_create(
            publication=publication,
            researcher=researcher,
        )
    )

    return relationship, created

def extract_centre_researchers(html):
    """
    Extract researchers belonging to the target Centre directly from
    the Centre page.

    A researcher profile may appear several times in the HTML. Some
    occurrences use the person's full name while others use citation
    abbreviations such as "Turner, A.". The function therefore keeps
    the most descriptive name found for each unique profile URL.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    researchers = {}

    def name_quality(name):
        """
        Give preference to normal full names over abbreviated
        citation-style names.

        For example, "Andy Turner" should be preferred over
        "Turner, A." for the same profile URL.
        """

        score = len(name)

        # Citation-style names frequently contain commas or periods,
        # so reduce their score when a cleaner display name exists.
        if "," in name:
            score -= 20

        if "." in name:
            score -= 10

        return score

    for link in soup.find_all("a", href=True):
        href = link.get("href")

        if href.startswith("/"):
            full_url = (
                "https://pureportal.coventry.ac.uk"
                + href
            )
        else:
            full_url = href

        # Ignore the generic persons directory and retain only
        # individual PurePortal researcher profiles.
        if (
            full_url
            and "/en/persons/" in full_url
            and full_url.rstrip("/")
            != "https://pureportal.coventry.ac.uk/en/persons"
        ):
            name = link.get_text(
                " ",
                strip=True,
            )

            if not name:
                continue

            existing_name = researchers.get(
                full_url
            )

            # Keep whichever label looks more like a complete
            # human-readable researcher name.
            if (
                existing_name is None
                or name_quality(name)
                > name_quality(existing_name)
            ):
                researchers[full_url] = name

    return [
        {
            "name": name,
            "profile_url": profile_url,
        }
        for profile_url, name in sorted(
            researchers.items()
        )
    ]

def crawl_and_save_centre_researchers():
    """
    Crawl the target Centre page, discover its researcher profiles,
    visit each permitted profile politely, and save the researchers
    into Oracle.

    Individual profile pages are used for the final researcher name
    because the Centre page often displays abbreviated citation names
    such as "Turner, A." instead of the full profile name.

    The function continues with the remaining researchers if one
    individual profile cannot be processed.
    """

    centre_response = fetch_page(CENTRE_URL)

    centre_researchers = extract_centre_researchers(
        centre_response.text
    )

    results = {
        "discovered": len(centre_researchers),
        "created": 0,
        "updated": 0,
        "failed": 0,
    }

    for item in centre_researchers:
        profile_url = item["profile_url"]

        try:
            profile_response = fetch_page(
                profile_url
            )

            details = extract_researcher_details(
                profile_response.text,
                profile_url,
            )

            researcher, created = save_researcher(
                details
            )

            if researcher is None:
                results["failed"] += 1
                continue

            if created:
                results["created"] += 1
            else:
                results["updated"] += 1

            print(
                f"Saved researcher: "
                f"{researcher.name}"
            )

        except Exception as error:
            results["failed"] += 1

            print(
                f"Could not process "
                f"{profile_url}: {error}"
            )

    return results

def link_publication_to_centre_researchers(
    publication,
    publication_details,
):
    """
    Link a saved publication with every author who belongs to the
    target Centre.

    Publication pages may contain authors from several institutions.
    Only author profile URLs that already exist in the RESEARCHERS
    table are linked. This ensures that the vertical search engine
    retains publications with verified Centre membership.
    """

    linked = 0
    already_linked = 0

    for profile_url in publication_details[
        "author_profile_links"
    ]:
        try:
            researcher = Researcher.objects.get(
                profile_url=profile_url
            )

        except Researcher.DoesNotExist:
            # The author is not one of the researchers discovered
            # from the target Centre, so no relationship is created.
            continue

        relationship, created = (
            link_publication_to_researcher(
                publication,
                researcher,
            )
        )

        if created:
            linked += 1
        else:
            already_linked += 1

    return {
        "linked": linked,
        "already_linked": already_linked,
    }

def crawl_and_save_publication(publication_url):
    """
    Process one PurePortal publication from beginning to end.

    The function:
    1. retrieves the publication politely,
    2. extracts its structured metadata,
    3. confirms that it belongs to the target Centre,
    4. saves or updates it in Oracle, and
    5. links it with verified Centre researchers.

    Keeping these operations in one function makes the crawler easier
    to reuse later when processing many publication URLs.
    """

    response = fetch_page(
        publication_url
    )

    details = extract_publication_details(
        response.text,
        publication_url,
    )

    # Keep only publications that have at least one verified author
    # belonging to the target Centre.
    if not publication_has_centre_author(
        details
    ):
        return {
        "saved": False,
        "reason": (
            "No verified Centre author found"
        ),
        "publication": None,
    }

    publication, created = save_publication(
        details
    )

    linking_result = (
        link_publication_to_centre_researchers(
            publication,
            details,
        )
    )

    return {
        "saved": True,
        "created": created,
        "publication": publication,
        "linked": linking_result["linked"],
        "already_linked": linking_result[
            "already_linked"
        ],
    }

def discover_publication_urls_from_researchers():
    """
    Discover publication URLs from every verified Centre researcher
    currently stored in Oracle.

    Each researcher profile is fetched politely and its visible
    PurePortal publication links are collected. A set is used to
    remove duplicates because the same publication may appear on
    several co-authors' profiles.
    """

    publication_urls = set()

    researchers = Researcher.objects.all().order_by(
        "researcher_id"
    )

    for researcher in researchers:
        try:
            response = fetch_page(
                researcher.profile_url
            )

            details = extract_researcher_details(
                response.text,
                researcher.profile_url,
            )

            researcher_links = details[
                "publication_links"
            ]

            publication_urls.update(
                researcher_links
            )

            print(
                f"{researcher.name}: "
                f"{len(researcher_links)} "
                f"publication links found"
            )

        except Exception as error:
            print(
                f"Could not inspect "
                f"{researcher.name}: {error}"
            )

    return sorted(publication_urls)

def publication_has_centre_author(publication_details):
    """
    Check whether a publication has at least one verified author from
    the target Centre.

    The Centre's researcher profiles have already been discovered and
    stored in the RESEARCHERS table. A publication is therefore
    eligible when at least one of its author profile URLs matches a
    researcher stored in that verified Centre list.
    """

    author_profile_links = publication_details.get(
        "author_profile_links",
        [],
    )

    if not author_profile_links:
        return False

    return Researcher.objects.filter(
        profile_url__in=author_profile_links
    ).exists()

def crawl_and_save_discovered_publications():
    """
    Discover publication URLs from verified Centre researcher
    profiles and process each unique publication.

    Every publication is fetched politely, checked for at least one
    verified Centre author, saved to Oracle, and linked with its
    Centre researchers.

    A summary is returned so the crawler's behaviour can later be
    displayed in the Django interface and discussed in the report.
    """

    publication_urls = (
        discover_publication_urls_from_researchers()
    )

    results = {
        "discovered": len(publication_urls),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
    }

    for number, publication_url in enumerate(
        publication_urls,
        start=1,
    ):
        try:
            print(
                f"Processing publication "
                f"{number}/{len(publication_urls)}"
            )

            result = crawl_and_save_publication(
                publication_url
            )

            if not result["saved"]:
                results["skipped"] += 1
                print(
                    f"Skipped: "
                    f"{result.get('reason')}"
                )
                continue

            if result["created"]:
                results["created"] += 1
            else:
                results["updated"] += 1

            print(
                f"Saved: "
                f"{result['publication'].title}"
            )

        except Exception as error:
            results["failed"] += 1

            print(
                f"Could not process "
                f"{publication_url}: {error}"
            )

    return results