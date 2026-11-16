import re
import datetime
from typing import Dict, List


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _alias_patterns(alias: str) -> List[re.Pattern]:
    alias = " ".join(str(alias).strip().split())
    if not alias:
        return []

    patterns = [re.compile(re.escape(alias), re.IGNORECASE)]

    compact_alias = _compact(alias)
    if compact_alias and compact_alias != alias.lower():
        flexible = r"[\W_]*".join(map(re.escape, compact_alias))
        patterns.append(re.compile(flexible, re.IGNORECASE))

    return patterns


def paper_mentions_target(paper: Dict, gene: str, aliases: List[str]) -> bool:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
    if gene.lower() not in text.lower():
        return False
    return any(
        pattern.search(text)
        for alias in aliases
        for pattern in _alias_patterns(alias)
    )


def rank_papers(papers: List[Dict], gene: str, aliases: List[str]) -> List[Dict]:
    """
    Rank studies based on recency, study type, journal, and variant mention confidence.
    """
    current_year = datetime.datetime.now().year
    ranked_papers = []

    for paper in papers:
        if not paper_mentions_target(paper, gene, aliases):
            continue

        score = 0.0
        abstract = paper.get("abstract", "").lower()
        title = paper.get("title", "").lower()
        journal = paper.get("journal", "").lower()
        year = paper.get("year")

        # 1. Recency Weight (Max 10 points)
        if year:
            age = current_year - year
            if age <= 2:
                score += 10
            elif age <= 5:
                score += 8
            elif age <= 10:
                score += 5
            else:
                score += 2
        else:
            score += 0

        # 2. Study Type Weight (Prioritize Meta-analyses, Functional, and Large Cohorts)
        # Check title and abstract for keywords
        if "meta-analysis" in abstract or "meta-analysis" in title:
            score += 8
        elif "functional" in abstract or "in vitro" in abstract or "in vivo" in abstract:
            score += 6
        elif "cohort" in abstract or "case-control" in abstract or "population" in abstract:
            score += 5
        elif "case report" in abstract or "case series" in abstract:
            score += 2

        # 3. Journal Impact Weight (Approximation using genetics/high impact journals)
        high_impact_journals = [
            "nature", "science", "nejm", "lancet", "jama", "cell", 
            "american journal of human genetics", "human mutation", 
            "clinical cancer research", "journal of clinical oncology",
            "plos genetics", "genetics in medicine", "nucleic acids research"
        ]
        if any(j in journal for j in high_impact_journals):
            score += 5

        # 4. Variant Mention Confidence (Max 10 points)
        # Exact/Alias match check
        exact_matches = 0
        for alias in aliases:
            if any(pattern.search(f"{title} {abstract}") for pattern in _alias_patterns(alias)):
                exact_matches += 1

        if exact_matches > 0:
            score += min(15, 8 + (exact_matches * 2))

        # Save score and add to list
        paper_copy = paper.copy()
        paper_copy["ranking_score"] = score
        ranked_papers.append(paper_copy)

    # Sort descending by ranking score
    ranked_papers.sort(key=lambda x: x["ranking_score"], reverse=True)
    return ranked_papers
