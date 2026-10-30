"""Fetch brain-cancer abstracts from PubMed into the SQLite buffer.
(Same PubMed query as v1; now also captures the article title for citations.)"""
import requests
import xml.etree.ElementTree as ET
import logging
from .buffer import SQLiteBuffer

logger = logging.getLogger(__name__)

PUBMED_QUERY = (
    "(brain OR cerebral OR glioma OR meningioma OR medulloblastoma "
    "OR oligodendroglioma) AND (MRI OR imaging OR radiogenomic* OR "
    "radiomic* OR spectroscopy OR PET) AND (gene OR mutation OR IDH1 OR "
    "TP53 OR EGFR OR MGMT OR TERT OR BRAF OR methylation)"
)


def fetch_abstracts_pubmed(nbr: int, buffer: SQLiteBuffer) -> int:
    """Search PubMed, fetch abstracts, store in buffer. Returns #added."""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed", "term": PUBMED_QUERY, "retmax": nbr,
        "retmode": "json", "sort": "relevance",
    }
    try:
        r = requests.get(search_url, params=search_params, timeout=15)
        r.raise_for_status()
        idlist = r.json()["esearchresult"]["idlist"]
        if not idlist:
            logger.warning("No PubMed articles found for the query.")
            return 0
    except requests.RequestException as e:
        logger.error(f"PubMed search error: {e}")
        return 0

    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    fetch_params = {"db": "pubmed", "id": ",".join(idlist),
                    "retmode": "xml", "rettype": "abstract"}
    try:
        r = requests.get(fetch_url, params=fetch_params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"PubMed fetch error: {e}")
        return 0

    return _parse_and_store(r.text, buffer)


def _parse_and_store(xml_content: str, buffer: SQLiteBuffer) -> int:
    count = 0
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return 0

    for article in root.findall(".//PubmedArticle"):
        pmid_elem = article.find(".//PMID")
        title_elem = article.find(".//ArticleTitle")
        # an article can have several AbstractText sections (Background/Methods/...)
        abstract_parts = [
            "".join(a.itertext()).strip()
            for a in article.findall(".//AbstractText")
        ]
        abstract_text = " ".join(p for p in abstract_parts if p).strip()
        if pmid_elem is not None and abstract_text:
            pmid = pmid_elem.text
            title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""
            if buffer.add_abstract(pmid, abstract_text, title):
                count += 1
    return count
