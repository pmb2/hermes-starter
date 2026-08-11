#!/usr/bin/env python3
"""
ai_ecosystem_scan.py - Bleeding-edge AI/ML ecosystem scanner.
Searches arXiv across 8 frontier categories + GitHub Trending.
See intelligence-pulse skill reference: ai-ecosystem-scanning.md

Usage: python ai_ecosystem_scan.py
"""
import json, sys, time, xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from pathlib import Path

ARXIV_URL = "https://export.arxiv.org/api/query"
NS = {'a': 'http://www.w3.org/2005/Atom'}
NL = chr(10)

QUERIES = [
    ("Agent Frameworks & Tool Calling", "cat:cs.AI+AND+ti:agent+OR+ti:tool+OR+ti:orchestration+ANDNOT+ti:medical+ANDNOT+ti:robotic+ANDNOT+ti:health", 8),
    ("LLM Reasoning & RL", "ti:reasoning+AND+ti:language+model+OR+ti:reinforcement+learning+AND+cat:cs.LG", 5),
    ("Fine-Tuning (GRPO/DPO/RLHF)", "ti:fine-tuning+AND+ti:RL+OR+ti:DPO+OR+ti:GRPO+OR+ti:preference+AND+cat:cs.LG", 5),
    ("Model Architecture (MoE/Sparse)", "ti:mixture+of+experts+OR+ti:sparse+OR+ti:quantization+OR+ti:distillation+AND+cat:cs.LG", 5),
    ("Context & Inference Optimization", "ti:context+AND+ti:window+OR+ti:inference+AND+ti:optimization+AND+cat:cs.CL", 5),
    ("AI Coding & Software Engineering", "ti:code+generation+AND+ti:agent+OR+ti:program+repair+OR+ti:software+engineering+AND+cat:cs.SE", 5),
    ("Multi-Agent Systems", "ti:multi-agent+OR+ti:multiagent+AND+cat:cs.AI+AND+cat:cs.MA", 5),
    ("Safety & Alignment", "ti:safety+AND+ti:alignment+OR+ti:jailbreak+OR+ti:red+teaming+AND+cat:cs.AI", 5),
]

def fetch_arxiv(search_query, max_results=5):
    url = f"{ARXIV_URL}?search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    try:
        req = Request(url, headers={"User-Agent": "HermesAI/1.0"})
        with urlopen(req, timeout=30) as resp:
            root = ET.parse(resp).getroot()
            entries = []
            for entry in root.findall('a:entry', NS):
                title = entry.find('a:title', NS)
                title_text = title.text.strip().replace(NL, ' ') if title is not None else "?"
                arxiv_id = entry.find('a:id', NS)
                id_text = arxiv_id.text.strip().split('/abs/')[-1] if arxiv_id is not None else "?"
                pub = entry.find('a:published', NS)
                pub_text = pub.text[:10] if pub is not None else "?"
                authors_el = entry.findall('a:author', NS)
                authors = ", ".join(a.find('a:name', NS).text.split()[-1] for a in authors_el if a.find('a:name', NS) is not None)[:80] if authors_el else "?"
                entries.append({"title": title_text[:120], "id": id_text, "date": pub_text, "authors": authors, "url": f"https://arxiv.org/abs/{id_text}"})
            return entries
    except Exception as e:
        return [{"title": f"Error: {e}", "id": "", "date": "", "authors": "", "url": ""}]

def fetch_github_trending():
    try:
        req = Request("https://api.github.com/search/repositories?q=ai+llm+agent+framework&sort=stars&order=desc&per_page=10",
                      headers={"User-Agent": "HermesAI/1.0", "Accept": "application/vnd.github.v3+json"})
        with urlopen(req, timeout=15) as resp:
            data = json.load(resp)
            return [{"name": r["full_name"], "stars": r["stargazers_count"], "desc": (r["description"] or "-")[:100], "url": r["html_url"], "lang": r["language"] or "?"} for r in data.get("items", [])[:10]]
    except Exception as e:
        return [{"name": f"GitHub error: {e}", "stars": 0, "desc": "", "url": "", "lang": ""}]

def main():
    output = [f"AI Ecosystem Scan — {__import__('datetime').datetime.now().strftime('%a %b %d %H:%M ET')}", ""]
    papers = 0
    for label, query, limit in QUERIES:
        time.sleep(3.5)
        entries = fetch_arxiv(query, limit)
        valid = [e for e in entries if e["id"] and "Error" not in e["title"]]
        if not valid: continue
        papers += len(valid)
        output.append(f">> {label} ({len(valid)} papers)")
        for e in valid:
            output.append(f"  [{e['date']}] {e['title']}\n   {e['authors']}\n   {e['url']}")
        output.append("")
    if not papers: output.append("No new papers found. arXiv may be rate-limiting.\n")
    repos = fetch_github_trending()
    valid_repos = [r for r in repos if "Error" not in r["name"]]
    if valid_repos:
        output.append(f">> GitHub Trending AI/ML ({len(valid_repos)} repos)")
        for r in valid_repos[:8]:
            output.append(f"  ★{r['stars']} [{r['lang']}] {r['name']}\n   {r['desc']}\n   {r['url']}")
    print(NL.join(output))

if __name__ == "__main__":
    main()
