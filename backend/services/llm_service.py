import os
import json
import requests
from typing import Dict, List, Optional

class LLMService:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
    def _call_openai(self, prompt: str, system_prompt: str, json_mode: bool = False) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}"
        }
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}
            
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_anthropic(self, prompt: str, system_prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": 4000,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()["content"][0]["text"]

    def _call_gemini(self, prompt: str, system_prompt: str, json_mode: bool = False) -> str:
        # Use Google's Developer API for Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={self.gemini_key}"
        headers = {
            "Content-Type": "application/json"
        }
        # In Gemini 1.5, we can specify system instructions
        data = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        if json_mode:
            data["generationConfig"]["responseMimeType"] = "application/json"
            
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]

    def generate(self, prompt: str, system_prompt: str, json_mode: bool = False) -> str:
        # Check keys and use the first available
        try:
            if self.openai_key:
                return self._call_openai(prompt, system_prompt, json_mode)
            elif self.anthropic_key:
                return self._call_anthropic(prompt, system_prompt)
            elif self.gemini_key:
                return self._call_gemini(prompt, system_prompt, json_mode)
            else:
                # Fallback mock for local development if no API keys are available
                print("Warning: No LLM API keys found. Using mock response.")
                if json_mode:
                    if "clinical_interpretation" in prompt or "summarize" in system_prompt.lower():
                        return json.dumps({
                            "key_findings": [
                                "Variant observed in multiple patients with hereditary breast cancer and absent in controls.",
                                "Functional assays show damaging effect on homologous recombination activity.",
                                "Extremely low frequency in population databases."
                            ],
                            "acmg_table": [
                                {"criterion": "PS4", "strength": "Strong", "justification": "Variant significantly enriched in affected individuals vs controls."},
                                {"criterion": "PM2", "strength": "Moderate", "justification": "Absent from large population control databases (gnomAD)."},
                                {"criterion": "PS3", "strength": "Strong", "justification": "Well-established in vitro functional studies show loss of function."}
                            ],
                            "clinical_interpretation": "Pathogenic",
                            "uncertainties": [
                                "Precise penetrance estimates require further large-scale prospective cohort studies."
                            ],
                            "confidence_score": 89.0
                        })
                    else:
                        return json.dumps({
                            "evidence": [
                                {
                                    "evidence_type": "case_control",
                                    "finding": "Observed in 12 breast cancer patients and absent in controls.",
                                    "strength": "moderate",
                                    "acmg_code": "PS4",
                                    "justification": "Prevalence of variant is significantly increased in affected individuals."
                                },
                                {
                                    "evidence_type": "population",
                                    "finding": "Absent in gnomAD population database.",
                                    "strength": "moderate",
                                    "acmg_code": "PM2",
                                    "justification": "Absent from population databases."
                                },
                                {
                                    "evidence_type": "functional",
                                    "finding": "In vitro homologous recombination repair assay showed <10% wildtype activity.",
                                    "strength": "strong",
                                    "acmg_code": "PS3",
                                    "justification": "Functional study shows damaging effect."
                                }
                            ]
                        })
                return "Mock summary: Variant analysis mock result."
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise e

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates 1536-dimensional embeddings for pgvector.
        Falls back to mock/zero vector if API key is not available.
        """
        if self.openai_key:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_key}"
            }
            data = {
                "model": "text-embedding-3-small", # outputs 1536 dim
                "input": text
            }
            try:
                response = requests.post(url, headers=headers, json=data, timeout=15)
                response.raise_for_status()
                return response.json()["data"][0]["embedding"]
            except Exception as e:
                print(f"Error getting OpenAI embedding: {e}")
        
        # Fallback to dummy 1536 float array if no key
        return [0.0] * 1536
