import requests
import xml.etree.ElementTree as ET
from .buffer import SQLiteBuffer
import logging

logger = logging.getLogger(__name__)

def fetch_abstracts_pubmed(nbr: int, buffer: SQLiteBuffer) -> int:
    """
    Extrait les résumés (abstracts) de PubMed et les stocke dans le buffer.
    Retourne le nombre d'abstracts ajoutés.
    """
    # 1. Recherche des IDs d'articles
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": (
            "(brain OR cerebral OR glioma OR meningioma OR medulloblastoma "
            "OR oligodendroglioma) AND (MRI OR imaging OR radiogenomic* OR "
            "radiomic* OR spectroscopy OR PET) AND (gene OR mutation OR IDH1 OR "
            "TP53 OR EGFR OR MGMT OR TERT OR BRAF OR methylation)"
        ),
        "retmax": nbr,
        "retmode": "json",
        "sort": "relevance"
    }
    
    try:
        search_response = requests.get(search_url, params=search_params, timeout=10)
        search_response.raise_for_status()
        idlist = search_response.json()["esearchresult"]["idlist"]
        if not idlist:
            logger.warning("Aucun article trouvé pour les termes de recherche.")
            return 0
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la recherche sur PubMed : {e}")
        return 0

    # 2. Récupération des détails des articles
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(idlist),
        "retmode": "xml",
        "rettype": "abstract"
    }
    
    try:
        fetch_response = requests.get(fetch_url, params=fetch_params, timeout=20)
        fetch_response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la récupération des abstracts sur PubMed : {e}")
        return 0
    
    # 3. Parsing du XML et stockage dans le buffer
    return _parse_and_store(fetch_response.text, buffer)

def _parse_and_store(xml_content: str, buffer: SQLiteBuffer) -> int:
    """Parse le contenu XML et stocke les abstracts dans le buffer."""
    count = 0
    try:
        root = ET.fromstring(xml_content)
        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            abstract_elem = article.find(".//AbstractText")

            if pmid_elem is not None and abstract_elem is not None:
                pmid = pmid_elem.text
                abstract_text = ''.join(abstract_elem.itertext()).strip()
                if pmid and abstract_text:
                    buffer.add_abstract(pmid, abstract_text)
                    count += 1
    except ET.ParseError as e:
        logger.error(f"Erreur de parsing XML : {e}")
    
    return count

