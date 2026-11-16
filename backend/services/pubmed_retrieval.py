import requests
import xml.etree.ElementTree as ET
import re
from typing import List, Dict


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for value in values:
        cleaned = " ".join(str(value).strip().split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            deduped.append(cleaned)
    return deduped


def _searchable_aliases(aliases: List[str]) -> List[str]:
    """
    Keep variant-like aliases and discard full ClinVar titles, which are too long
    to be useful as exact PubMed phrases and can make searches return nothing.
    """
    searchable = []
    for alias in aliases:
        alias = " ".join(str(alias).strip().split())
        if not alias or len(alias) > 80:
            continue

        extracted = []
        extracted.extend(re.findall(r"\b[cpgnmr]\.[A-Za-z0-9_*?>_+\-]+", alias))
        extracted.extend(re.findall(r"\brs\d+\b", alias, re.IGNORECASE))
        extracted.extend(re.findall(r"\bp\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}\w*", alias))
        searchable.extend(extracted)

        if (":" in alias or "(" in alias) and extracted:
            continue

        if re.search(r"\b[cpgnmr]\.", alias, re.IGNORECASE):
            searchable.append(alias)
        elif re.search(r"\brs\d+\b", alias, re.IGNORECASE):
            searchable.append(alias)
        elif re.search(r"\b(?:del|dup|ins|fs|splice|missense|nonsense)\b", alias, re.IGNORECASE):
            searchable.append(alias)
        elif re.search(r"[A-Z][a-z]{2}\d+[A-Z][a-z]{2}", alias):
            searchable.append(alias)
    return _dedupe(searchable)


def build_pubmed_query(gene: str, aliases: List[str]) -> str:
    gene = gene.strip()
    alias_queries = [
        f'"{alias}"[Title/Abstract]'
        for alias in _searchable_aliases(aliases)
    ]
    gene_query = f'"{gene}"[Title/Abstract]'
    if not alias_queries:
        return gene_query
    return f"({gene_query}) AND ({' OR '.join(alias_queries)})"


def search_pubmed(gene: str, aliases: List[str], limit: int = 100) -> List[str]:
    """
    Search PubMed using E-utilities and return a list of PMIDs.
    """
    print("GENE:", gene)
    print("ALIASES:", aliases)

    query = build_pubmed_query(gene, aliases)
    print("PUBMED QUERY:", query)

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": limit,
        "sort": "relevance",
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print("PUBMED URL:", response.url)
        print("PUBMED RESULT:", response.text[:500])
        data = response.json()

        pmids = data.get("esearchresult", {}).get("idlist", [])

        print("PMIDS:", pmids)

        return pmids
    except Exception as e:
        print(f"Error searching PubMed: {e}")
        return []

def fetch_paper_details(pmids: List[str]) -> List[Dict]:
    """
    Fetch paper details (Title, Journal, Year, Abstract, Authors) using efetch.fcgi.
    """
    if not pmids:
        return []
    
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }
    
    papers = []
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code != 200:
            return []
        
        root = ET.fromstring(response.content)
        
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""
            
            title_el = article.find(".//ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else "No Title"
            
            # Extract Abstract
            abstract_texts = article.findall(".//AbstractText")
            abstract_parts = []
            for el in abstract_texts:
                label = el.attrib.get("Label")
                text = " ".join("".join(el.itertext()).split())
                if not text:
                    continue
                abstract_parts.append(f"{label}: {text}" if label else text)
            abstract = " ".join(abstract_parts)
            
            # Extract Journal
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else ""
            
            # Extract Year
            year_el = article.find(".//JournalIssue/PubDate/Year")
            if year_el is not None:
                year = int(year_el.text)
            else:
                # Try MedlineDate
                medline_date = article.find(".//JournalIssue/PubDate/MedlineDate")
                if medline_date is not None and medline_date.text:
                    match = re.search(r'\b(19|20)\d{2}\b', medline_date.text)
                    year = int(match.group(0)) if match else None
                else:
                    year = None
                    
            papers.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "year": year
            })
            
    except Exception as e:
        print(f"Error fetching paper details: {e}")
        
    return papers
