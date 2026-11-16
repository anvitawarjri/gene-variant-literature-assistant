import json
from typing import Dict, List
from services.llm_service import LLMService

class EvidenceExtractor:
    def __init__(self):
        self.llm = LLMService()

    def extract_evidence_from_abstract(self, gene: str, variant: str, abstract: str) -> List[Dict]:
        system_prompt = (
            "You are an expert clinical genomics assistant. Your task is to analyze the provided scientific literature abstract "
            "and extract clinical evidence regarding a specific genetic variant. "
            "You must map this evidence to ACMG (American College of Medical Genetics) criteria where appropriate.\n\n"
            "ACMG Criteria reference:\n"
            "- PS3: Functional studies show damaging effect\n"
            "- PM2: Absent or extremely low frequency in population databases\n"
            "- PP1: Co-segregation with disease in affected family members\n"
            "- PS4: Prevalence of the variant in affected individuals is significantly increased compared with controls\n"
            "- BP4/PP3: Computational evidence (damage/benign prediction)\n"
            "- BS3: Functional studies show no damaging effect\n\n"
            "Rules:\n"
            "1. ONLY extract evidence explicitly stated in the abstract. Do not invent or extrapolate.\n"
            "2. Map to ACMG codes ONLY if the abstract provides direct supporting observations (e.g., segregation, case-control count, functional assays).\n"
            "3. If a criterion is met, specify the code, strength (Strong, Moderate, Supporting), and a clear clinical justification.\n"
            "4. Return the results strictly as a JSON object with a key 'evidence' containing an array of evidence items."
        )

        prompt = (
            f"Target Gene: {gene}\n"
            f"Target Variant: {variant}\n\n"
            f"Abstract:\n{abstract}\n\n"
            "Please extract all evidence. Output format:\n"
            "{\n"
            '  "evidence": [\n'
            '    {\n'
            '      "evidence_type": "case_control" | "functional" | "population" | "segregation" | "computational" | "clinical_significance",\n'
            '      "finding": "Description of the finding",\n'
            '      "strength": "Strong" | "Moderate" | "Supporting",\n'
            '      "acmg_code": "PS4" | "PS3" | "PM2" | "PP1" | "PP3" | "BP4" | null,\n'
            '      "justification": "Explanation of ACMG code mapping"\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        try:
            response_text = self.llm.generate(prompt, system_prompt, json_mode=True)
            # Parse the JSON response
            data = json.loads(response_text)
            return data.get("evidence", [])
        except Exception as e:
            print(f"Error during evidence extraction: {e}")
            return []
            
    def summarize_evidence(self, gene: str, variant: str, evidence_list: List[Dict]) -> Dict:
        """
        Summarize all extracted evidence into a unified report.
        """
        system_prompt = (
            "You are a clinical genomics assistant. Your job is to analyze a compilation of extracted scientific literature "
            "evidence for a specific genetic variant, and generate a final structured interpretation summary.\n\n"
            "Include:\n"
            "1. Key findings (bulleted list of evidence)\n"
            "2. ACMG evidence table\n"
            "3. Clinical interpretation statement (pathogenic, likely pathogenic, VUS, likely benign, benign)\n"
            "4. Remaining uncertainties\n\n"
            "Rules:\n"
            "- Never invent evidence.\n"
            "- Use ONLY the supplied evidence items.\n"
            "- Cite the source paper details if provided.\n"
            "- Output JSON format."
        )

        evidence_str = json.dumps(evidence_list, indent=2)
        prompt = (
            f"Target Gene: {gene}\n"
            f"Target Variant: {variant}\n\n"
            f"Extracted Evidence Items:\n{evidence_str}\n\n"
            "Generate the final summary. Output format:\n"
            "{\n"
            '  "key_findings": ["Finding 1", "Finding 2"],\n'
            '  "acmg_table": [\n'
            '    {"criterion": "PS4", "strength": "Strong", "justification": "..."}\n'
            '  ],\n'
            '  "clinical_interpretation": "Pathogenic",\n'
            '  "uncertainties": ["Uncertainty 1"],\n'
            '  "confidence_score": 85.0\n'
            "}"
        )

        try:
            response_text = self.llm.generate(prompt, system_prompt, json_mode=True)
            return json.loads(response_text)
        except Exception as e:
            print(f"Error during evidence summarization: {e}")
            return {
                "key_findings": ["Error generating summary"],
                "acmg_table": [],
                "clinical_interpretation": "Uncertain",
                "uncertainties": [str(e)],
                "confidence_score": 0.0
            }
