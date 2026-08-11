# Infrastructure Technology Evaluation Example: Kubernetes Assessment

> **Context:** 2026-05-30 session — evaluated the operator's full stack (50+ repos, 13 Docker Compose stacks, 101 containers on a single Windows 10 machine with 1× RTX 3090) for Kubernetes adoption.
>
> **Use this as a concrete example of the methodology in `infrastructure-technology-evaluation`.**

## Key Findings

- **101 containers** spread across 13 Docker Compose stacks — all on a single Windows 10 desktop via Docker Desktop (WSL2)
- **1× RTX 3090 GPU** shared across Qwen 35B, Qwen 14B, ComfyUI, Whisper, Ollama — severe contention
- **80+ Docker volumes**, **13+ PostgreSQL instances**, **19 networks**
- **Solo operator** — no dedicated DevOps resources
- **Single-GPU ceiling** means K8s can't improve GPU utilization until 2+ GPU machines exist

## Verdict: ⏳ Not Ready But High Potential

K8s *could* solve real pain points (auto-healing, rolling updates, resource quotas, scaling) but the cost of migration today outweighs benefits. The single biggest factor: **one machine + one GPU** means K8s loses most of its value.

## Tiers

| Tier | Count | Examples |
|------|-------|---------|
| Tier 1: K8s candidates | 7 | n8n workers, LiteLLM, frontends |
| Tier 2: Conditional | 6 | Twenty CRM, NocoDB, Nextcloud, Fonoster |
| Tier 3: Stay on Docker | 8+ | All GPU workloads, Supabase, Postgres instances |
| Tier 4: Fine as-is | 4+ | BurnBounty, ConstructManage, YT-Animations |

## Phases

| Phase | Timeline | What | Prerequisite |
|-------|----------|------|-------------|
| 0 | Now | Resource limits, health checks, compose profiles, backup pipeline | Nothing |
| 1 | 3-6 months | K3s on VPS, migrate stateless workloads, ArgoCD GitOps | Second machine |
| 2 | 6-12 months | Multi-cluster (VPS CPU + local GPU), service mesh, full HA | Second GPU machine |

## Key Red Flags

- Single GPU = K8s can't improve GPU workload scheduling
- 80+ volume migration = the hardest part, don't underestimate
- Solo operator overhead = 5-10 hrs/week cluster maintenance
- DevEx regression: `docker compose up -d --build` is faster than K8s build→push→apply→wait

## Single Most Impactful Decision

> **Get a second machine.** A $200 used mini-PC transforms K8s from "operational overhead" to "actual value." Without it, Phase 0 (Docker-native improvements) is the right stop.
