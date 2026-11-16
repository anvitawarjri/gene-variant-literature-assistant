import requests
import re
from typing import Dict, List, Optional


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


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


def _variant_matches(target_variant: str, candidate: str) -> bool:
    target = _compact(target_variant)
    return bool(target and target in _compact(candidate))

def validate_hgvs(variant: str) -> bool:
    """
    Basic check for HGVS nomenclature formatting.
    Covers common patterns like c.123A>G, p.Arg456Gly, c.68_69delAG, etc.
    """
    # Simple regex checking for common genomic, coding, or protein prefixes
    pattern = r'^[cgpmsr]\.[a-zA-Z0-9_*?>_+-]+$'
    return bool(re.match(pattern, variant))

def get_gene_info(gene_symbol: str) -> Optional[Dict]:
    """
    Queries NCBI Gene database to verify the gene symbol exists.
    """
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&term={gene_symbol}[Gene%20Name]+AND+human[Organism]&retmode=json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return None
        
        # Get gene summary
        gene_id = id_list[0]
        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gene&id={gene_id}&retmode=json"
        summary_resp = requests.get(summary_url, timeout=10)
        summary_data = summary_resp.json()
        
        gene_info = summary_data.get("result", {}).get(gene_id, {})
        return {
            "gene_id": gene_id,
            "symbol": gene_info.get("name"),
            "description": gene_info.get("description"),
            "synonyms": gene_info.get("otheraliases", "").split(", ")
        }
    except Exception as e:
        print(f"Error querying NCBI Gene: {e}")
        return None

def get_clinvar_aliases(gene: str, variant: str) -> List[str]:
    """
    Queries ClinVar to find aliases for the variant.
    Only extracts aliases if the ClinVar record belongs to the target gene.
    """
    aliases = [variant]
    query = f"{gene} {variant}"
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    try:
        response = requests.get(
            url,
            params={"db": "clinvar", "term": query, "retmode": "json", "retmax": 20},
            timeout=10,
        )

        print("URL:", response.url)
        print("STATUS:", response.status_code)
        print("BODY:", response.text[:500])

        id_list = response.json().get("esearchresult", {}).get("idlist", [])

        print("CLINVAR QUERY:", query)
        print("CLINVAR IDS:", id_list)

        if not id_list:
            return aliases
        
        # Fetch ClinVar summary
        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id={','.join(id_list[:100])}&retmode=json"
        summary_resp = requests.get(summary_url, timeout=10)
        results = summary_resp.json().get("result", {})
        
        for uid in id_list[:100]:
            var_data = results.get(uid, {})
            title = var_data.get("title")

            print("TITLE:", title)

            if title:
                # ONLY extract aliases if this ClinVar record matches our target gene
                # E.g., title contains "(BRCA1)"
                if f"({gene})".lower() not in title.lower():
                    continue
                if not _variant_matches(variant, title):
                    continue
                    
                # Extract protein representation if present, e.g. p.Glu23Valfs
                p_match = re.search(r'\((p\.[^\)]+)\)', title)
                if p_match:
                    aliases.append(p_match.group(1))
                # Extract coding representation, e.g. c.68_69delAG
                c_match = re.search(r':\s*(c\.[^\s\(]+)', title)
                if c_match:
                    aliases.append(c_match.group(1))
            
            # Extract variation set info if the gene is correct
            if title and f"({gene})".lower() in title.lower() and _variant_matches(variant, title):
                var_set = var_data.get("variation_set", [])
                for item in var_set:
                    cdna = item.get("cdna")
                    protein = item.get("protein")
                    if cdna:
                        aliases.append(cdna)
                    if protein:
                        aliases.append(protein)
    except Exception as e:
        print(f"Error querying ClinVar aliases: {e}")
    
    # Deduplicate and clean
    return _dedupe(aliases)
