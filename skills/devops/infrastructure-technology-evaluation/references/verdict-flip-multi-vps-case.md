# Case Study: Verdict Flip from Single-Node to Multi-Node

> **Context:** 2026-05-30 session — same user (the operator), same stack (101 containers, 13 Docker Compose stacks, 1× RTX 3090), but two different evaluation questions producing opposite K8s verdicts.
>
> **Use this as a concrete example of the verdict-sensitivity-to-node-count principle.**

## The Two Evaluations

### v1: Single-Machine Evaluation (2026-05-30)

**Question:** "Evaluate my full stack for Kubernetes adoption."

**Assumed topology:**
- 1 Windows 10 machine (Docker Desktop, WSL2)
- 1× RTX 3090 GPU
- 101 containers, 13 stacks
- 1 Oracle Cloud free-tier VPS (lightweight)

**Verdict:** ⏳ **Not Ready — But High Potential**

**Key reasoning:**
- Single GPU = K8s can't improve GPU scheduling until 2+ GPU machines
- Single machine = K8s on 1 node loses HA, scheduling decisions, pod spread
- 80+ Docker volumes = volume migration is the hardest problem, don't attempt
- 13 migration projects = too many, tier workloads and only move what makes sense
- Solo operator = 5-10 hrs/week cluster maintenance overhead

**Recommendation:** Phase 0 (Docker-native improvements) only. Revisit when a second machine is available.

### v2: Multi-VPS, Client Services Evaluation (2026-05-30)

**Question:** "What if I'm using my local server + multiple VPS providers + adding more for client services?"

**Assumed topology:**
- Same local Windows 10 machine + RTX 3090
- Multiple VPS instances (Oracle + additional providers)
- Client web apps and services added regularly
- Growing number of machines to manage

**Verdict:** ✅ **Ready** — For client workloads. GPU stays on local Docker.

**Key reasoning:**
- 3+ machines = multi-node K8s actually delivers real value (scheduling, spread, HA)
- Client isolation = namespaces + network policies replace "separate VPS per client"
- GitOps = ArgoCD replaces "SSH into N different servers"
- Standardized deploy = Helm charts replace "bespoke Docker Compose per client"
- Scaling = add VPS node to cluster, not "buy a bigger VPS"
- Client onboarding = 1-2 hours (PR + merge + ArgoCD syncs) vs 1-2 days (buy VPS, configure, deploy)

**Key nuance:** The verdict only applies to NEW client workloads and a few stateless apps. The existing 101-container internal stack stays on Docker Compose.

## The Lesson

**The same infrastructure can warrant opposite K8s recommendations depending on topology and business model.**

| Dimension | Single Machine | Multi-Machine + Clients |
|-----------|---------------|------------------------|
| **K8s value** | Low (single node) | High (multi-node scheduling, HA) |
| **Pain K8s solves** | Few (Docker improvements suffice) | Many (unified control plane, GitOps, isolation) |
| **Cost of NOT adopting** | Low (Docker Compose works fine) | High (SSH snowflakes × N servers) |
| **Business leverage** | None (internal ops) | High (standardized client pipeline) |

**When evaluating K8s, always ask:**
1. How many machines / VPS nodes? (1 = mostly not worth it, 2+ = reconsider)
2. Do you serve clients? (Internal-only = Docker improvements suffice, client-facing = K8s unlocks business value)
3. What stays on Docker? (GPU, complex stacks, high-data-gravity = stay. New apps, stateless services = move)
