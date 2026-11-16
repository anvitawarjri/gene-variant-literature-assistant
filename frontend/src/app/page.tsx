"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Search,
  BookOpen,
  Activity,
  FileText,
  MessageSquare,
  Sparkles,
  AlertCircle,
  Loader2,
  ChevronRight,
  ExternalLink,
  ThumbsUp,
  HelpCircle,
  Dna,
  RefreshCw,
  Send,
  ShieldAlert
} from "lucide-react";

interface Paper {
  pmid: string;
  title: string;
  journal: string;
  year: number;
  abstract: string;
  ranking_score: number;
}

interface ACMGRow {
  criterion: string;
  strength: string;
  justification: string;
}

interface AnalysisSummary {
  key_findings: string[];
  acmg_table: ACMGRow[];
  clinical_interpretation: string;
  uncertainties: string[];
  confidence_score: number;
}

interface ChatMessage {
  sender: "user" | "ai";
  text: string;
}

export default function Home() {
  const [gene, setGene] = useState("");
  const [variant, setVariant] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState("");

  // Results
  const [variantId, setVariantId] = useState<number | null>(null);
  const [aliases, setAliases] = useState<string[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [summary, setSummary] = useState<AnalysisSummary | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);

  // Chat
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { sender: "ai", text: "Hello! Once the report is generated, you can ask questions about the papers, ACMG criteria, or functional studies here." }
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleDemoInput = (demoGene: string, demoVariant: string) => {
    setGene(demoGene);
    setVariant(demoVariant);
  };

  const handleSearchAndAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gene.trim() || !variant.trim()) return;

    setIsLoading(true);
    setError("");
    setSummary(null);
    setPapers([]);
    setVariantId(null);
    setAliases([]);

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      // Step 1: Search literature
      setLoadingStep("Validating variant and searching PubMed...");
      const searchRes = await fetch(`${backendUrl}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gene: gene.trim(), variant: variant.trim() })
      });

      if (!searchRes.ok) {
        const errData = await searchRes.json();
        throw new Error(errData.detail || "Search failed.");
      }

      const searchData = await searchRes.json();
      setVariantId(searchData.variant_id);
      setAliases(searchData.aliases || []);
      setPapers(Array.isArray(searchData.papers) ? searchData.papers : []);

      if (!searchData.papers || searchData.papers.length === 0) {
        setIsLoading(false);
        setError("No publications found for this variant. Please check the spelling or nomenclature.");
        return;
      }

      // Step 2: Analyze variant
      setLoadingStep("Extracting evidence and mapping ACMG criteria using LLM...");
      const analyzeRes = await fetch(`${backendUrl}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ variant_id: searchData.variant_id })
      });

      if (!analyzeRes.ok) {
        const errData = await analyzeRes.json();
        throw new Error(errData.detail || "Analysis failed.");
      }

      const analyzeData = await analyzeRes.json();
      setSummary(analyzeData.summary);

      // Update chat session with greeting tailored to variant
      setChatMessages([
        {
          sender: "ai",
          text: `Analysis complete for ${gene} ${variant}. I have loaded ${searchData.papers.length} publications. How can I help you interpret this variant?`
        }
      ]);

    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
      setLoadingStep("");
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput.trim();
    setChatInput("");
    setChatMessages(prev => [...prev, { sender: "user", text: userText }]);
    setIsChatLoading(true);

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      const res = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userText,
          variant_id: variantId
        })
      });

      if (!res.ok) {
        throw new Error("Failed to get chat response.");
      }

      const data = await res.json();
      setChatMessages(prev => [...prev, { sender: "ai", text: data.answer }]);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { sender: "ai", text: "Sorry, I encountered an error answering your question. Please try again." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const sendQuickQuestion = (question: string) => {
    setChatInput(question);
    // Submit using a small timeout so state update propagates
    setTimeout(() => {
      const form = document.getElementById("chat-form") as HTMLFormElement;
      form?.requestSubmit();
    }, 50);
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-white/5 glass-panel sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-cyan-500/10 p-2 rounded-xl border border-cyan-500/20">
            <Dna className="w-6 h-6 text-cyan-400 animate-pulse-slow" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              Variant Literature Assistant
              <span className="text-[10px] uppercase font-semibold bg-cyan-500/15 text-cyan-400 px-2 py-0.5 rounded-full border border-cyan-500/25">
                AI Agent
              </span>
            </h1>
            <p className="text-xs text-slate-400">Pathogenicity classification & literature evidence engine</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-2 bg-slate-900 px-3 py-1.5 rounded-lg border border-white/5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            PubMed & ACMG Engines Connected
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full flex flex-col gap-6">

        {/* Search Panel */}
        <section className="glass-panel rounded-2xl p-6 border border-white/10 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none -ml-20 -mb-20"></div>

          <div className="max-w-3xl">
            <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              Analyze Genetic Variant
            </h2>
            <p className="text-sm text-slate-400 mb-6">
              Enter a HGVS genomic or protein variant. The assistant will search PubMed, retrieve relevant papers, extract clinical evidence, and map findings directly to ACMG classification criteria.
            </p>

            <form onSubmit={handleSearchAndAnalyze} className="flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="gene" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Gene Symbol</label>
                  <input
                    type="text"
                    id="gene"
                    value={gene}
                    onChange={(e) => setGene(e.target.value)}
                    placeholder="e.g. BRCA1, TP53"
                    className="bg-slate-950/80 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all placeholder:text-slate-600"
                    required
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="variant" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Variant Representation</label>
                  <input
                    type="text"
                    id="variant"
                    value={variant}
                    onChange={(e) => setVariant(e.target.value)}
                    placeholder="e.g. c.68_69delAG, p.R175H"
                    className="bg-slate-950/80 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all placeholder:text-slate-600"
                    required
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full md:w-auto bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-medium rounded-xl px-6 py-3 text-sm shadow-lg hover:shadow-cyan-500/20 active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    Retrieve & Classify
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Demos */}
            <div className="mt-4 flex flex-wrap gap-2 items-center text-xs">
              <span className="text-slate-500">Quick Demos:</span>
              <button
                onClick={() => handleDemoInput("BRCA1", "c.68_69delAG")}
                className="bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg px-2.5 py-1 transition-all text-cyan-300"
              >
                BRCA1 c.68_69delAG
              </button>
              <button
                onClick={() => handleDemoInput("TP53", "p.R175H")}
                className="bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg px-2.5 py-1 transition-all text-cyan-300"
              >
                TP53 p.R175H
              </button>
            </div>
          </div>
        </section>

        {/* Error message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3 text-sm text-red-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Analysis Failed</span>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Loading overlay/screen */}
        {isLoading && (
          <div className="glass-panel border border-white/10 rounded-2xl p-12 flex flex-col items-center justify-center text-center gap-4 min-h-[300px]">
            <Loader2 className="w-12 h-12 text-cyan-400 animate-spin" />
            <div className="max-w-md">
              <p className="text-base font-semibold text-slate-200">Retrieving Information</p>
              <p className="text-sm text-slate-400 mt-1 animate-pulse">{loadingStep}</p>
            </div>
          </div>
        )}

        {/* Report & Data Dashboard */}
        {!isLoading && summary && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Left/Middle Panels: Literature & RAG Chat */}
            <div className="lg:col-span-2 flex flex-col gap-6">

              {/* Publication List Panel */}
              <div className="glass-panel border border-white/10 rounded-2xl p-6 flex flex-col gap-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-base font-bold flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-cyan-400" />
                    Retrieved & Ranked Literature ({papers.length})
                  </h3>
                  <span className="text-[10px] text-slate-500">Sorted by relevance & quality score</span>
                </div>

                <div className="flex flex-col gap-3 max-h-[380px] overflow-y-auto pr-1">
                  {papers.map((paper, idx) => (
                    <div
                      key={paper.pmid}
                      onClick={() => setSelectedPaper(selectedPaper?.pmid === paper.pmid ? null : paper)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer text-left relative ${selectedPaper?.pmid === paper.pmid
                        ? "bg-cyan-500/5 border-cyan-500/30"
                        : "bg-slate-950/40 border-white/5 hover:bg-slate-900/50 hover:border-white/10"
                        }`}
                    >
                      <div className="absolute top-4 right-4 flex items-center gap-1.5">
                        <span className="text-[10px] bg-slate-900 px-2 py-0.5 rounded border border-white/5 font-semibold text-slate-400">
                          Score: {paper.ranking_score.toFixed(1)}
                        </span>
                      </div>

                      <span className="text-[10px] text-cyan-400 font-semibold uppercase tracking-wide">
                        {paper.journal} • {paper.year || "Unknown"}
                      </span>
                      <h4 className="text-sm font-semibold mt-1 text-slate-100 line-clamp-2 pr-16">{paper.title}</h4>

                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-xs text-slate-400">PMID: {paper.pmid}</span>
                        <a
                          href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-500 hover:text-cyan-400 transition-colors"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>

                      {selectedPaper?.pmid === paper.pmid && (
                        <div className="mt-4 pt-4 border-t border-white/5 text-xs text-slate-300 leading-relaxed">
                          <p className="font-semibold text-slate-200 mb-1">Abstract:</p>
                          {paper.abstract}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Chat RAG Panel */}
              <div className="glass-panel border border-white/10 rounded-2xl p-6 flex flex-col h-[480px]">
                <h3 className="text-base font-bold flex items-center gap-2 mb-4">
                  <MessageSquare className="w-4 h-4 text-cyan-400" />
                  Variant RAG Chat Assistant
                </h3>

                {/* Messages Box */}
                <div className="flex-1 overflow-y-auto mb-4 p-4 bg-slate-950/60 border border-white/5 rounded-xl flex flex-col gap-3">
                  {chatMessages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex flex-col max-w-[85%] ${msg.sender === "user" ? "self-end items-end" : "self-start items-start"
                        }`}
                    >
                      <span className="text-[10px] text-slate-500 mb-0.5">
                        {msg.sender === "user" ? "You" : "Variant AI Agent"}
                      </span>
                      <div
                        className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed ${msg.sender === "user"
                          ? "bg-indigo-600/80 text-white rounded-tr-none border border-indigo-500/20"
                          : "bg-slate-900 border border-white/10 text-slate-200 rounded-tl-none"
                          }`}
                      >
                        {msg.text}
                      </div>
                    </div>
                  ))}
                  {isChatLoading && (
                    <div className="self-start flex items-center gap-2 text-xs text-slate-500 mt-1">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      AI is formulating response based on literature...
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Quick prompts */}
                <div className="flex gap-2 overflow-x-auto pb-3 text-xs">
                  <button
                    onClick={() => sendQuickQuestion("Show the strongest functional evidence from these studies.")}
                    className="flex-shrink-0 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg px-3 py-1.5 transition-all text-slate-300"
                  >
                    What functional studies exist?
                  </button>
                  <button
                    onClick={() => sendQuickQuestion("Why was PS4 assigned?")}
                    className="flex-shrink-0 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg px-3 py-1.5 transition-all text-slate-300"
                  >
                    Why was PS4 assigned?
                  </button>
                  <button
                    onClick={() => sendQuickQuestion("Is there any population database evidence for this variant?")}
                    className="flex-shrink-0 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg px-3 py-1.5 transition-all text-slate-300"
                  >
                    Show PM2/population details
                  </button>
                </div>

                {/* Input form */}
                <form id="chat-form" onSubmit={handleSendMessage} className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask a question about the variant evidence..."
                    className="flex-1 bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500/50"
                  />
                  <button
                    type="submit"
                    disabled={isChatLoading}
                    className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold p-2.5 rounded-xl transition-all disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>

            </div>

            {/* Right Panel: Clinical Interpretation Report */}
            <div className="lg:col-span-1 flex flex-col gap-6">

              {/* Report Panel */}
              <div className="glass-panel border border-white/10 rounded-2xl p-6 flex flex-col gap-6 relative">

                {/* Confidence Meter */}
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold flex items-center gap-2">
                    <FileText className="w-4 h-4 text-cyan-400" />
                    Structured Evidence Report
                  </h3>
                  <div className="relative w-12 h-12 flex items-center justify-center">
                    {/* Ring background */}
                    <svg className="w-full h-full transform -rotate-90">
                      <circle
                        cx="24"
                        cy="24"
                        r="20"
                        className="stroke-white/5"
                        strokeWidth="3.5"
                        fill="transparent"
                      />
                      <circle
                        cx="24"
                        cy="24"
                        r="20"
                        className="stroke-cyan-500"
                        strokeWidth="3.5"
                        fill="transparent"
                        strokeDasharray={125}
                        strokeDashoffset={125 - (125 * (summary?.confidence_score || 0)) / 100}
                      />
                    </svg>
                    <span className="absolute text-[10px] font-bold text-cyan-400">
                      {summary?.confidence_score}%
                    </span>
                  </div>
                </div>

                {/* Variant Header Info */}
                <div className="bg-slate-950/60 p-4 border border-white/5 rounded-xl">
                  <div className="text-[10px] text-slate-500 uppercase font-semibold">Target Variant</div>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">{gene} {variant}</div>

                  {aliases.length > 1 && (
                    <div className="mt-2 pt-2 border-t border-white/5">
                      <span className="text-[10px] text-slate-500 block mb-1">Aliases detected:</span>
                      <div className="flex flex-wrap gap-1">
                        {aliases.map((alias, idx) => (
                          alias !== variant ? (
                            <span key={idx} className="bg-white/5 text-[10px] text-slate-300 px-2 py-0.5 rounded border border-white/5">
                              {alias}
                            </span>
                          ) : null
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Primary Classification Badge */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Preliminary Classification</span>
                  <div className={`rounded-xl px-4 py-3 border font-semibold text-sm flex items-center gap-2 ${summary?.clinical_interpretation?.toLowerCase()?.includes("pathogenic")
                    ? "bg-red-500/10 border-red-500/20 text-red-400"
                    : summary?.clinical_interpretation?.toLowerCase()?.includes("benign")
                      ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                      : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                    }`}>
                    <ShieldAlert className="w-4 h-4" />
                    {summary?.clinical_interpretation || "Uncertain"}
                  </div>
                </div>

                {/* ACMG Evidence Mapping Table */}
                <div className="flex flex-col gap-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">ACMG Evidence Mapping</span>
                  <div className="border border-white/5 rounded-xl overflow-hidden bg-slate-950/40">
                    <table className="w-full text-xs text-left border-collapse">
                      <thead>
                        <tr className="border-b border-white/5 bg-slate-900/50">
                          <th className="px-3 py-2 text-slate-400 font-semibold">Code</th>
                          <th className="px-3 py-2 text-slate-400 font-semibold">Strength</th>
                          <th className="px-3 py-2 text-slate-400 font-semibold">Criterion Justification</th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary?.acmg_table && summary.acmg_table.length > 0 ? (
                          summary.acmg_table.map((row, idx) => (
                            <tr key={idx} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                              <td className="px-3 py-2.5 font-bold text-cyan-400">{row.criterion}</td>
                              <td className="px-3 py-2.5">
                                <span className="bg-white/5 px-2 py-0.5 rounded border border-white/5 text-[10px] font-semibold text-slate-300">
                                  {row.strength}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 text-slate-300 leading-normal">{row.justification}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={3} className="px-3 py-4 text-center text-slate-500">
                              No ACMG codes mapped.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Key Findings */}
                <div className="flex flex-col gap-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Key Findings Summary</span>
                  <ul className="flex flex-col gap-2">
                    {summary?.key_findings?.map((finding, idx) => (
                      <li key={idx} className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/30 p-2.5 border border-white/5 rounded-lg">
                        <ChevronRight className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                        <span className="leading-relaxed">{finding}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Remaining Uncertainties */}
                {summary?.uncertainties && summary.uncertainties.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-amber-500/80">Remaining Uncertainties</span>
                    <ul className="flex flex-col gap-1.5">
                      {summary.uncertainties?.map((unc, idx) => (
                        <li key={idx} className="text-xs text-slate-400 flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-500/50 mt-1.5 flex-shrink-0"></span>
                          <span className="leading-relaxed">{unc}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* References PMIDs */}
                <div className="border-t border-white/5 pt-4">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Sources (Citations)</span>
                  <div className="flex flex-wrap gap-2">
                    {papers.map((paper) => (
                      <a
                        key={paper.pmid}
                        href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}`}
                        target="_blank"
                        rel="noreferrer"
                        className="bg-slate-900 border border-white/10 hover:border-cyan-500/30 text-xs px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-colors group"
                      >
                        <span className="text-slate-400 font-medium">PMID:</span>
                        <span className="text-cyan-400 group-hover:text-cyan-300 font-semibold">{paper.pmid}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500" />
                      </a>
                    ))}
                  </div>
                </div>

              </div>
            </div>

          </div>
        )}

      </main>
    </div>
  );
}


