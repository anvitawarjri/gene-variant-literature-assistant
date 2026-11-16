import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import math

# Database imports
from database import init_db, get_db, Variant, Paper, Evidence, Report

# Service imports
from services.variant_processing import validate_hgvs, get_gene_info, get_clinvar_aliases
from services.pubmed_retrieval import search_pubmed, fetch_paper_details
from services.evidence_ranking import paper_mentions_target, rank_papers
from services.evidence_extraction import EvidenceExtractor
from services.llm_service import LLMService

app = FastAPI(
    title="AI-Powered Variant Literature Assistant",
    description="API for fetching and analyzing variant literature.",
    version="1.0.0"
)

# Enable CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

class SearchRequest(BaseModel):
    gene: str
    variant: str

class AnalyzeRequest(BaseModel):
    variant_id: int

class ChatRequest(BaseModel):
    question: str
    variant_id: Optional[int] = None

def paper_to_dict(paper: Paper) -> Dict:
    return {
        "pmid": paper.pmid,
        "title": paper.title or "",
        "abstract": paper.abstract or "",
        "journal": paper.journal or "",
        "year": paper.year,
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to the Variant Literature Assistant API"}

@app.post("/search")
def search_literature(request: SearchRequest, db: Session = Depends(get_db)):
    # 1. Validate gene
    gene_info = get_gene_info(request.gene)
    if not gene_info:
        raise HTTPException(status_code=400, detail=f"Gene symbol '{request.gene}' not found in NCBI database.")

    # 2. Validate HGVS format
    if not validate_hgvs(request.variant):
        # We'll allow it but print a warning or proceed if ClinVar finds aliases
        print(f"Warning: Variant '{request.variant}' doesn't strictly match standard HGVS format.")

    # 3. Detect variant aliases via ClinVar
    aliases = get_clinvar_aliases(request.gene, request.variant)
    if request.variant not in aliases:
        aliases.append(request.variant)

    # 4. Save variant to DB (if not exists)
    db_variant = db.query(Variant).filter(
        Variant.gene == request.gene, 
        Variant.variant == request.variant
    ).first()
    if not db_variant:
        db_variant = Variant(gene=request.gene, variant=request.variant)
        db.add(db_variant)
        db.commit()
        db.refresh(db_variant)

    # 5. Search PubMed
    pmids = search_pubmed(request.gene, aliases, limit=100)
    print("PMIDS:", pmids)
    if not pmids:
        return {
            "variant_id": db_variant.id,
            "gene": db_variant.gene,
            "variant": db_variant.variant,
            "aliases": aliases,
            "papers": [],
            "message": "No papers found in PubMed for this variant."
        }

    # 6. Fetch papers details
    papers_data = fetch_paper_details(pmids)

    # 7. Rank papers
    ranked_papers = rank_papers(papers_data, request.gene, aliases)

    # 8. Save papers in DB & generate embeddings
    llm = LLMService()
    saved_papers = []
    for paper in ranked_papers:
        db_paper = db.query(Paper).filter(Paper.pmid == paper["pmid"]).first()
        if not db_paper:
            # Generate embedding
            embedding = llm.get_embedding(paper["abstract"] or paper["title"])
            db_paper = Paper(
                pmid=paper["pmid"],
                title=paper["title"],
                journal=paper["journal"],
                year=paper["year"],
                abstract=paper["abstract"],
                embedding=embedding
            )
            db.add(db_paper)
            db.commit()
            db.refresh(db_paper)
        
        saved_papers.append({
            "pmid": db_paper.pmid,
            "title": db_paper.title,
            "journal": db_paper.journal,
            "year": db_paper.year,
            "abstract": db_paper.abstract,
            "ranking_score": paper.get("ranking_score", 0)
        })

    return {
        "variant_id": db_variant.id,
        "gene": db_variant.gene,
        "variant": db_variant.variant,
        "aliases": aliases,
        "papers": saved_papers
    }

@app.post("/analyze")
def analyze_variant(request: AnalyzeRequest, db: Session = Depends(get_db)):
    # 1. Fetch variant
    variant = db.query(Variant).filter(Variant.id == request.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found.")

    # 2. Fetch ClinVar aliases to search papers in DB
    aliases = get_clinvar_aliases(variant.gene, variant.variant)
    if variant.variant not in aliases:
        aliases.append(variant.variant)

    # 3. Find matching papers from database
    all_papers = db.query(Paper).all()
    matching_papers = []
    for paper in all_papers:
        if paper_mentions_target(paper_to_dict(paper), variant.gene, aliases):
            matching_papers.append(paper)

    print("TOTAL PAPERS:", len(all_papers))
    print("GENE:", variant.gene)
    print("VARIANT:", variant.variant)
    print("ALIASES:", aliases)
    print("MATCHING PAPERS:", len(matching_papers))     


    if not matching_papers:
        raise HTTPException(status_code=400, detail="No papers cached for this variant. Please run /search first.")

    # 4. Extract evidence from each paper using LLM
    extractor = EvidenceExtractor()
    llm = LLMService()
    all_evidence = []

    for paper in matching_papers:
        # Check if evidence already extracted for this paper
        existing_evidence = db.query(Evidence).filter(Evidence.paper_id == paper.pmid).all()
        if existing_evidence:
            for ev in existing_evidence:
                all_evidence.append({
                    "paper_id": ev.paper_id,
                    "evidence_type": ev.evidence_type,
                    "evidence_text": ev.evidence_text,
                    "acmg_code": ev.acmg_code,
                    "strength": ev.strength
                })
        else:
            # Extract new evidence
            extracted = extractor.extract_evidence_from_abstract(variant.gene, variant.variant, paper.abstract)
            for item in extracted:
                embedding = llm.get_embedding(item["finding"])
                db_ev = Evidence(
                    paper_id=paper.pmid,
                    evidence_type=item.get("evidence_type"),
                    evidence_text=item.get("finding"),
                    acmg_code=item.get("acmg_code"),
                    strength=item.get("strength"),
                    embedding=embedding
                )
                db.add(db_ev)
                db.commit()
                db.refresh(db_ev)
                
                all_evidence.append({
                    "paper_id": db_ev.paper_id,
                    "evidence_type": db_ev.evidence_type,
                    "evidence_text": db_ev.evidence_text,
                    "acmg_code": db_ev.acmg_code,
                    "strength": db_ev.strength
                })

    # 5. Summarize evidence into a single report
    summary = extractor.summarize_evidence(variant.gene, variant.variant, all_evidence)

    # 6. Save report in DB
    import json
    report = Report(
        variant_id=variant.id,
        generated_summary=json.dumps(summary),
        confidence_score=summary.get("confidence_score", 0.0)
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "variant_id": variant.id,
        "summary": summary
    }

@app.get("/report/{id}")
def get_report(id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    
    import json
    try:
        summary_data = json.loads(report.generated_summary)
    except:
        summary_data = report.generated_summary

    variant = db.query(Variant).filter(Variant.id == report.variant_id).first()

    return {
        "report_id": report.id,
        "variant_id": report.variant_id,
        "gene": variant.gene if variant else "Unknown",
        "variant": variant.variant if variant else "Unknown",
        "summary": summary_data,
        "confidence_score": report.confidence_score,
        "created_at": report.created_at
    }

@app.get("/papers/{pmid}")
def get_paper(pmid: str, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.pmid == pmid).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper

def cosine_similarity(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(a * a for a in v1))
    magnitude_v2 = math.sqrt(sum(a * a for a in v2))
    if magnitude_v1 == 0 or magnitude_v2 == 0:
        return 0.0
    return dot_product / (magnitude_v1 * magnitude_v2)

@app.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Generate embedding for query
    llm = LLMService()
    query_emb = llm.get_embedding(request.question)

    # 2. Retrieve relevant context from DB
    # We will compute cosine similarity against papers and evidence in DB
    # Get evidence entries
    evidences = db.query(Evidence).all()
    # Filter by variant if provided
    if request.variant_id:
        # Get papers for variant
        variant = db.query(Variant).filter(Variant.id == request.variant_id).first()
        if variant:
            aliases = get_clinvar_aliases(variant.gene, variant.variant)
            if variant.variant not in aliases:
                aliases.append(variant.variant)
            # Find evidences belonging to matching papers
            evidences = [
                ev for ev in evidences
                if ev.paper and paper_mentions_target(paper_to_dict(ev.paper), variant.gene, aliases)
            ]

    # Rank evidence based on vector similarity
    ranked_ev = []
    for ev in evidences:
        if ev.embedding:
            sim = cosine_similarity(query_emb, ev.embedding)
            ranked_ev.append((sim, ev))
    ranked_ev.sort(key=lambda x: x[0], reverse=True)

    # Compile top 5 evidence texts
    context_str = "Relevant extracted findings:\n"
    for sim, ev in ranked_ev[:5]:
        context_str += f"- [PMID: {ev.paper_id}] Code: {ev.acmg_code or 'N/A'}, Text: {ev.evidence_text} (similarity: {sim:.2f})\n"

    # Also search paper abstracts
    papers = db.query(Paper).all()
    if request.variant_id:
        variant = db.query(Variant).filter(Variant.id == request.variant_id).first()
        if variant:
            aliases = get_clinvar_aliases(variant.gene, variant.variant)
            if variant.variant not in aliases:
                aliases.append(variant.variant)
            papers = [
                paper for paper in papers
                if paper_mentions_target(paper_to_dict(paper), variant.gene, aliases)
            ]
    ranked_papers = []
    for paper in papers:
        if paper.embedding:
            sim = cosine_similarity(query_emb, paper.embedding)
            ranked_papers.append((sim, paper))
    ranked_papers.sort(key=lambda x: x[0], reverse=True)

    context_str += "\nRelevant paper abstracts:\n"
    for sim, paper in ranked_papers[:3]:
        abstract = paper.abstract or ""
        context_str += f"- [PMID: {paper.pmid}] Title: {paper.title}\nAbstract: {abstract[:300]}...\n"

    # 3. Call LLM with RAG prompt
    system_prompt = (
        "You are an expert clinical genomics assistant. Use the provided scientific context to answer the user's question. "
        "Strictly adhere to the provided facts. Do not invent details. Cite PMIDs in your answer."
    )
    
    prompt = (
        f"Context:\n{context_str}\n\n"
        f"Question: {request.question}\n\n"
        "Answer:"
    )

    try:
        answer = llm.generate(prompt, system_prompt)
        return {"question": request.question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
