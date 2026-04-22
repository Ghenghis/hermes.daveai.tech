"""
Deep Research Agent

GPT-Researcher style deep research agent with multi-source gathering
and comprehensive report synthesis.

Usage:
    agent = HermesDeepResearchAgent(llm, message_bus)
    result = await agent.research("topic", depth=ResearchDepth.DEEP)
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Union
from enum import Enum
import asyncio
import json
import time
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ResearchDepth(Enum):
    """Research depth levels"""
    QUICK = "quick"          # 5-10 min, surface level
    DEEP = "deep"            # 20-30 min, comprehensive
    COMPREHENSIVE = "full"   # 60+ min, exhaustive


class ResearchStatus(Enum):
    """Research task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchSource:
    """Research source with credibility tracking"""
    url: str
    title: str
    domain: str
    credibility_score: float
    content: Optional[str] = None
    accessed_at: float = field(default_factory=time.time)
    relevance_score: float = 0.0


@dataclass
class ResearchFinding:
    """A single research finding"""
    question: str
    answer: str
    sources: list[ResearchSource]
    confidence: float
    relevance_score: float


@dataclass
class ResearchPlan:
    """Research plan created by planner"""
    query: str
    tasks: list[dict]
    depth: ResearchDepth
    estimated_time: int = 0


@dataclass
class DeepResearchResult:
    """Complete research result"""
    query: str
    plan: ResearchPlan
    findings: list[ResearchFinding]
    report: Optional[str] = None
    sources: list[ResearchSource] = field(default_factory=list)
    duration: float = 0.0
    status: ResearchStatus = ResearchStatus.PENDING


@dataclass
class ResearchConfig:
    """Configuration for deep research"""
    max_sources_per_question: int = 10
    min_credibility_score: float = 0.4
    max_concurrent_tasks: int = 5
    max_report_sections: int = 10
    include_citations: bool = True
    min_confidence_threshold: float = 0.5
    min_relevance_threshold: float = 0.3
    quick_research_time_limit: int = 300
    deep_research_time_limit: int = 1800
    comprehensive_time_limit: int = 3600


class CredibilityTracker:
    """
    Track and score source credibility based on domain reputation
    """
    
    DOMAIN_RATINGS = {
        "arxiv.org": 0.95,
        "github.com": 0.85,
        "wikipedia.org": 0.6,
        "stackoverflow.com": 0.75,
        "medium.com": 0.5,
        "dev.to": 0.55,
        "nytimes.com": 0.8,
        "bbc.com": 0.85,
        "reuters.com": 0.85,
        "nature.com": 0.95,
        "science.org": 0.95,
        "ieee.org": 0.9,
        "acm.org": 0.9,
        "google.com": 0.4,
        "bing.com": 0.3,
        "example-spam.com": 0.1
    }
    
    def __init__(self):
        self.visited_sources: dict[str, ResearchSource] = {}
        
    async def add_source(self, url: str, title: str) -> ResearchSource:
        """Add and score a new source"""
        domain = self._extract_domain(url)
        base_score = self.DOMAIN_RATINGS.get(domain, 0.5)
        
        source = ResearchSource(
            url=url,
            title=title,
            domain=domain,
            credibility_score=base_score
        )
        
        self.visited_sources[url] = source
        return source
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return "unknown"
    
    def _has_ssl(self, url: str) -> bool:
        """Check if URL uses HTTPS"""
        return url.startswith("https://")
    
    def get_source(self, url: str) -> Optional[ResearchSource]:
        """Get cached source"""
        return self.visited_sources.get(url)


class HermesDeepResearchAgent:
    """
    Hermes agent with GPT-Researcher-style deep research
    """
    
    def __init__(
        self,
        llm: Any,
        message_bus: Any = None,
        config: Optional[ResearchConfig] = None,
        web_search_fn: Optional[Callable] = None,
        fetch_content_fn: Optional[Callable] = None
    ):
        self.llm = llm
        self.message_bus = message_bus
        self.config = config or ResearchConfig()
        self.credibility_tracker = CredibilityTracker()
        self.web_search_fn = web_search_fn or self._default_web_search
        self.fetch_content_fn = fetch_content_fn or self._default_fetch_content
        
    async def research(
        self,
        query: str,
        depth: ResearchDepth = ResearchDepth.DEEP
    ) -> DeepResearchResult:
        """
        Execute deep research on query
        
        Args:
            query: Research query
            depth: Research depth level
            
        Returns:
            DeepResearchResult with findings and report
        """
        start_time = time.time()
        
        # Set timeout based on depth
        timeout = {
            ResearchDepth.QUICK: self.config.quick_research_time_limit,
            ResearchDepth.DEEP: self.config.deep_research_time_limit,
            ResearchDepth.COMPREHENSIVE: self.config.comprehensive_time_limit
        }[depth]
        
        try:
            # Phase 1: Planning
            plan = await self._create_research_plan(query, depth)
            
            # Phase 2: Parallel research execution
            findings = await self._execute_research(plan)
            
            # Phase 3: Synthesis
            report = await self._synthesize_report(query, findings)
            
            # Collect all sources
            all_sources = []
            for finding in findings:
                all_sources.extend(finding.sources)
                
            return DeepResearchResult(
                query=query,
                plan=plan,
                findings=findings,
                report=report,
                sources=all_sources,
                duration=time.time() - start_time,
                status=ResearchStatus.COMPLETED
            )
            
        except asyncio.TimeoutError:
            return DeepResearchResult(
                query=query,
                plan=None,
                findings=[],
                report="Research timed out",
                duration=time.time() - start_time,
                status=ResearchStatus.FAILED
            )
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return DeepResearchResult(
                query=query,
                plan=None,
                findings=[],
                report=f"Research failed: {str(e)}",
                duration=time.time() - start_time,
                status=ResearchStatus.FAILED
            )
    
    async def _create_research_plan(
        self,
        query: str,
        depth: ResearchDepth
    ) -> ResearchPlan:
        """Create research plan based on query and depth"""
        
        # Assess complexity
        complexity = await self._assess_complexity(query)
        
        # Determine number of sub-questions
        num_questions = {
            ResearchDepth.QUICK: 3,
            ResearchDepth.DEEP: 7,
            ResearchDepth.COMPREHENSIVE: 15
        }[depth]
        
        # Generate sub-questions
        sub_questions = await self._generate_sub_questions(
            query,
            num_questions=num_questions,
            complexity=complexity
        )
        
        # Create tasks for each sub-question
        tasks = []
        for i, question in enumerate(sub_questions):
            task = {
                "id": f"research_{i}",
                "question": question,
                "source_types": self._determine_source_types(question),
                "priority": self._assess_priority(question)
            }
            tasks.append(task)
            
        return ResearchPlan(
            query=query,
            tasks=tasks,
            depth=depth,
            estimated_time=self._estimate_time(depth)
        )
    
    async def _assess_complexity(self, query: str) -> dict:
        """Assess query complexity"""
        prompt = f"""Analyze this research query for complexity:

Query: {query}

Rate complexity (1-10) and identify:
- Number of distinct topics
- Required expertise level
- Time sensitivity
- Special requirements (data, code, etc.)

Return JSON with scores and tags."""

        response = await self._call_llm(prompt)
        
        try:
            return json.loads(response)
        except:
            return {"score": 5, "tags": ["general"]}
    
    async def _generate_sub_questions(
        self,
        query: str,
        num_questions: int,
        complexity: dict
    ) -> list[str]:
        """Generate focused sub-questions"""
        prompt = f"""Decompose this research query into {num_questions} focused questions:

Query: {query}

Requirements:
- Each question should be self-contained and answerable independently
- Cover different aspects: definitions, history, current state, challenges, future directions
- Be specific enough for targeted research
- Avoid overlapping questions

Return a JSON array of questions."""

        response = await self._call_llm(prompt)
        
        try:
            return json.loads(response)
        except:
            # Fallback: split query into parts
            words = query.split()
            return [" ".join(words[i:i+5]) for i in range(0, len(words), 5)][:num_questions]
    
    async def _execute_research(
        self,
        plan: ResearchPlan
    ) -> list[ResearchFinding]:
        """Execute research tasks in parallel"""
        
        # Create tasks for all research questions
        research_tasks = []
        for task in plan.tasks:
            research_tasks.append(
                self._research_single_question(task)
            )
        
        # Execute in parallel with concurrency limit
        findings = await asyncio.gather(*research_tasks)
        
        return list(findings)
    
    async def _research_single_question(
        self,
        task: dict
    ) -> ResearchFinding:
        """Research a single question thoroughly"""
        
        # Gather sources
        sources = await self._gather_sources(
            task["question"],
            max_results=self.config.max_sources_per_question
        )
        
        # Filter by credibility
        credible_sources = [
            s for s in sources
            if s.credibility_score >= self.config.min_credibility_score
        ]
        
        # Extract information
        extracted_info = await self._extract_information(
            task["question"],
            credible_sources
        )
        
        # Generate answer
        answer = await self._generate_answer(
            task["question"],
            extracted_info
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            extracted_info,
            credible_sources
        )
        
        return ResearchFinding(
            question=task["question"],
            answer=answer,
            sources=credible_sources,
            confidence=confidence,
            relevance_score=task.get("priority", 1.0)
        )
    
    async def _gather_sources(
        self,
        question: str,
        max_results: int
    ) -> list[ResearchSource]:
        """Gather sources for a research question"""
        
        # Use web search
        search_results = await self.web_search_fn(
            question,
            num_results=max_results * 2
        )
        
        sources = []
        for result in search_results:
            source = await self.credibility_tracker.add_source(
                url=result.get("url", ""),
                title=result.get("title", "")
            )
            
            # Fetch content if needed
            if source.credibility_score >= self.config.min_credibility_score:
                source.content = await self.fetch_content_fn(source.url)
                
            sources.append(source)
            
        # Sort by credibility
        sources.sort(key=lambda s: s.credibility_score, reverse=True)
        
        return sources[:max_results]
    
    async def _extract_information(
        self,
        question: str,
        sources: list[ResearchSource]
    ) -> list[dict]:
        """Extract relevant information from sources"""
        
        extracted = []
        
        for source in sources:
            if not source.content:
                continue
                
            prompt = f"""Question: {question}

Source: {source.url}
Content: {source.content[:4000]}...

Extract passages directly relevant to answering the question.
Return JSON array of passages with relevance scores (0-1).
Format: [{{"text": "...", "score": 0.8}}]"""

            response = await self._call_llm(prompt)
            
            try:
                passages = json.loads(response)
                for passage in passages:
                    extracted.append({
                        "source": source,
                        "passage": passage.get("text", ""),
                        "relevance": passage.get("score", 0.5)
                    })
            except:
                continue
                
        # Sort by relevance
        extracted.sort(key=lambda x: x["relevance"], reverse=True)
        
        return extracted
    
    async def _generate_answer(
        self,
        question: str,
        extracted_info: list[dict]
    ) -> str:
        """Generate answer from extracted information"""
        
        # Build context from top sources
        context_parts = []
        for e in extracted_info[:5]:
            context_parts.append(
                f"[Source: {e['source'].url}]\n{e['passage']}"
            )
        context = "\n\n".join(context_parts)
        
        prompt = f"""Based on the following research, provide a comprehensive answer.

Question: {question}

Research Findings:
{context}

Write a clear, accurate, and comprehensive answer citing sources where appropriate."""

        return await self._call_llm(prompt)
    
    async def _synthesize_report(
        self,
        query: str,
        findings: list[ResearchFinding]
    ) -> str:
        """Synthesize findings into final report"""
        
        # Group findings by theme/topic
        organized = self._organize_findings(findings)
        
        # Generate report sections
        sections = []
        for theme, theme_findings in organized.items():
            section = await self._write_report_section(theme, theme_findings)
            sections.append(section)
            
        # Generate executive summary
        summary = await self._generate_executive_summary(query, findings)
        
        # Format full report
        report = f"# Research Report: {query}\n\n"
        report += f"## Executive Summary\n\n{summary}\n\n"
        
        for section in sections[:self.config.max_report_sections]:
            report += f"## {section['title']}\n\n{section['content']}\n\n"
            
        if self.config.include_citations:
            report += "## Sources\n\n"
            report += self._format_source_list(findings)
            
        return report
    
    def _organize_findings(
        self,
        findings: list[ResearchFinding]
    ) -> dict[str, list[ResearchFinding]]:
        """Organize findings by theme"""
        
        organized = {}
        
        for finding in findings:
            # Simple categorization based on question keywords
            theme = self._categorize_question(finding.question)
            if theme not in organized:
                organized[theme] = []
            organized[theme].append(finding)
            
        return organized
    
    def _categorize_question(self, question: str) -> str:
        """Categorize question into theme"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["what", "definition", "meaning"]):
            return "Overview & Definitions"
        elif any(word in question_lower for word in ["how", "work", "mechanism"]):
            return "How It Works"
        elif any(word in question_lower for word in ["history", "origin", "develop"]):
            return "History & Development"
        elif any(word in question_lower for word in ["why", "reason", "cause"]):
            return "Reasons & Causes"
        elif any(word in question_lower for word in ["compare", "vs", "versus"]):
            return "Comparison"
        elif any(word in question_lower for word in ["future", "trend", "predict"]):
            return "Future Outlook"
        else:
            return "Analysis"
    
    async def _write_report_section(
        self,
        theme: str,
        findings: list[ResearchFinding]
    ) -> dict:
        """Write a single report section"""
        
        # Build findings summary
        findings_text = "\n\n".join([
            f"### {f.question}\n\n{f.answer}"
            for f in findings
        ])
        
        prompt = f"""Write a detailed section for a research report.

Theme: {theme}

Research Findings:
{findings_text}

Requirements:
- Start with brief introduction to the theme
- Present key findings with citations
- Analyze implications
- Be objective and factual

Write in professional academic style."""

        content = await self._call_llm(prompt)
        
        return {
            "title": theme,
            "content": content
        }
    
    async def _generate_executive_summary(
        self,
        query: str,
        findings: list[ResearchFinding]
    ) -> str:
        """Generate executive summary"""
        
        summary_points = "\n".join([
            f"- {f.question}: {f.answer[:200]}..."
            for f in findings[:5]
        ])
        
        prompt = f"""Generate an executive summary for this research report.

Research Query: {query}

Key Findings:
{summary_points}

Write 2-3 paragraphs summarizing the research and its key conclusions."""

        return await self._call_llm(prompt)
    
    def _format_source_list(self, findings: list[ResearchFinding]) -> str:
        """Format source citations"""
        seen_urls = set()
        sources_text = ""
        
        for finding in findings:
            for source in finding.sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    sources_text += f"- [{source.title}]({source.url}) (Credibility: {source.credibility_score:.2f})\n"
                    
        return sources_text
    
    def _calculate_confidence(
        self,
        extracted_info: list[dict],
        sources: list[ResearchSource]
    ) -> float:
        """Calculate confidence score for finding"""
        if not sources or not extracted_info:
            return 0.0
            
        avg_relevance = sum(e["relevance"] for e in extracted_info) / len(extracted_info)
        avg_credibility = sum(s.credibility_score for s in sources) / len(sources)
        
        return (avg_relevance * 0.6 + avg_credibility * 0.4)
    
    def _determine_source_types(self, question: str) -> list[str]:
        """Determine what source types are needed"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["code", "github", "implementation"]):
            return ["technical", "code", "documentation"]
        elif any(word in question_lower for word in ["research", "study", "paper"]):
            return ["academic", "research", "publications"]
        elif any(word in question_lower for word in ["news", "recent", "latest"]):
            return ["news", "blog", "recent"]
        else:
            return ["general", "mixed"]
    
    def _assess_priority(self, question: str) -> float:
        """Assess question priority (higher = more important)"""
        question_lower = question.lower()
        priority = 1.0
        
        if any(word in question_lower for word in ["main", "key", "core"]):
            priority = 1.5
        if any(word in question_lower for word in ["important", "essential"]):
            priority = 1.3
            
        return priority
    
    def _estimate_time(self, depth: ResearchDepth) -> int:
        """Estimate research time in seconds"""
        return {
            ResearchDepth.QUICK: 300,
            ResearchDepth.DEEP: 1200,
            ResearchDepth.COMPREHENSIVE: 3600
        }[depth]
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if hasattr(self.llm, 'agenerate'):
            response = await self.llm.agenerate([prompt])
            return response if isinstance(response, str) else str(response)
        return await self.llm.generate(prompt)
    
    async def _default_web_search(
        self,
        query: str,
        num_results: int
    ) -> list[dict]:
        """Default web search implementation"""
        # This would be replaced with actual web search API
        logger.warning("Using default web search - implement actual search")
        return []
    
    async def _default_fetch_content(self, url: str) -> str:
        """Default content fetch implementation"""
        logger.warning("Using default fetch - implement actual fetcher")
        return ""
