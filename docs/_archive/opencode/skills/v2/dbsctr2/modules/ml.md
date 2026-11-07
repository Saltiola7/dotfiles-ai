# DBSCTR2 Domain Module: ML / AI

**Applies when:** Task involves ML model training or serving, LLM calls (Bedrock, Gemini, OpenAI),
embeddings, classification pipelines, feature engineering, eval harnesses, or AI-powered analysis.

This module extends Phases 1 and 4 of core DBSCTR2 with ML/AI-specific patterns.
Covers both classical ML (scikit-learn, custom models) and LLM-as-external-source (API-based).

---

## Phase 1 Extensions (Domain)

### ML Domain Concepts

Name these explicitly in the bounded context:

| Concept | Definition | Example |
|---------|-----------|---------|
| **Feature** | Input signal to a model/classifier | `example_text_embedding` (dimension declared by model contract) |
| **Label** | Ground-truth classification or target | Taxonomy node assignment (verified by human) |
| **Prediction** | Model output before acceptance | LLM-assigned category before confidence check |
| **Confidence** | Score indicating prediction reliability | Cosine similarity to taxonomy centroid |
| **Threshold** | Decision boundary for accept/reject/escalate | Project-selected embedding cutoff, qualified by an evaluation sweep |
| **Tier** | Processing level in a waterfall/cascade | TF-IDF → Embedding → LLM (cost-ordered) |
| **Eval metric** | Acceptance criterion for model quality | Project-defined F1 and precision acceptance floors |
| **Drift** | Distribution shift in features or predictions | Embedding centroid shift exceeds the configured drift budget |

### Model Lineage

Document the full path from raw data to served predictions:

```
Synthetic training lineage:
  source: example_dataset.labeled_text
    → feature: project-selected, versioned text embedding model
    → training: classifier fitted to the versioned training split
    → artifact: example_model (versioned with training metadata)
    → serve: text classification endpoint

Synthetic inference lineage:
  input: example text batch
    → tier 1: inexpensive classifier with an evaluated acceptance threshold
    → tier 2: selected embedding model for unresolved inputs
    → tier 3: selected language model for remaining inputs
    → validation: allowed labels, confidence and cross-checks
    → output: example_predictions (label, confidence, tier)
```

### Tiered Architecture Pattern

When a single model approach fails on cost, accuracy, or latency — use a waterfall:

```
Tier design:
  tier 1: [cheap, fast, handles easy cases] → threshold → classified
  tier 2: [moderate cost, handles medium cases] → threshold → classified
  tier 3: [expensive, handles hard cases] → all remaining
  validation: [cross-check tier assignments for disagreements]

Per-tier contract:
  - Input: what falls through from prior tier
  - Threshold: decision boundary (document how derived — sweep, heuristic, etc.)
  - Output: classified subset + confidence scores
  - Cost: $ per item at this tier
  - Coverage: % of total items handled by this tier
```

**Rule:** Tier assignment must be deterministic — a given input goes to exactly one tier.

### Reproducibility Requirements

Document these in Phase 1 for any ML component:

| Requirement | Implementation |
|-------------|---------------|
| **Data version** | DVC-tracked datasets; `data.dvc` pins exact version |
| **Code version** | Git SHA at training time recorded in model metadata |
| **Random seed** | Fixed seed for all stochastic operations (split, init, sampling) |
| **Dependency pins** | `uv.lock` / `requirements.txt` for exact package versions |
| **Environment** | Docker image SHA or explicit Python version + platform |

---

## Phase 4 Extensions (Contract)

### Feature Contracts

Define expected properties of model inputs:

```python
class ExampleFeatureContract:
    """Synthetic illustration; actual values belong to the selected model contract."""
    dimensions: int = 128            # illustrative vector size, not a deployed model
    dtype: str = "float32"           # precision
    norm: str = "unit"               # L2-normalized for cosine comparisons
    null_policy: str = "reject"      # no null embeddings allowed
    staleness: str = "content-hash"  # recompute after source content changes
```

| Check | Implementation |
|-------|---------------|
| **Dimension match** | Assert vector length == expected before any computation |
| **Null/NaN rejection** | No null vectors enter the pipeline; fail at ingestion |
| **Normalization** | Assert L2 norm ≈ 1.0 for cosine-based lookups |
| **Staleness** | Re-compute embeddings when source content changes (content-hash trigger) |

### Eval Threshold Contracts (Acceptance Gates)

A model or prompt change MUST pass eval before deployment:

| Gate | Metric | Threshold | Action on breach |
|------|--------|-----------|-----------------|
| **Classification accuracy** | F1 (macro) | Project-defined acceptance floor | Block deployment |
| **Per-tier precision** | Precision per tier | Project-defined precision floor | Alert + review |
| **Regression check** | F1 delta from baseline | Configured maximum regression | Block deployment |
| **Coverage** | % items classified (not "unknown") | Configured coverage floor | Alert |
| **Cost ceiling** | $ per batch run | Configured batch budget | Block and request budget review |

**Rule:** Eval runs on a held-out ground-truth set (versioned, reviewed, never used for training).
Document GT set version, size, and last review date in the spec.

### Drift Contracts

Detect when the model's world has changed:

| Signal | Detection | Threshold | Action |
|--------|-----------|-----------|--------|
| **Feature drift** | Centroid shift (cosine distance between current vs baseline centroid) | Configured distance budget | Alert + re-evaluate |
| **Prediction drift** | Distribution of predicted classes shifts vs baseline | Configured divergence budget | Alert + investigate |
| **Volume anomaly** | Items-per-tier ratio shifts significantly | Configured historical tolerance | Alert |
| **Confidence drift** | Mean confidence score drops | Configured decline from baseline | Re-train signal |

**Rule:** Drift detection runs on every batch. Baseline is the eval run's distribution.

### LLM-as-External-Source Contracts

Treat every LLM API call as an external data source with contracts:

#### Input Contract (Prompt)

| Aspect | Contract |
|--------|----------|
| **Prompt template** | Versioned (git-tracked); changes require eval gate |
| **Input schema** | Structured input variables with types and constraints |
| **Context window** | Max tokens documented; truncation strategy explicit |
| **System prompt** | Immutable per-version; changes = new model version |

#### Output Contract (Response)

| Aspect | Contract |
|--------|----------|
| **Response schema** | Pydantic model for structured output; validate before use |
| **Allowed values** | Enum constraints (e.g., category ∈ taxonomy nodes) |
| **Null handling** | What happens when LLM returns unexpected/empty/malformed output |
| **Confidence extraction** | How confidence is derived (LLM self-report vs embedding proxy) |

Example:
```python
class ClassificationResponse(BaseModel):
    """LLM classification output contract."""
    category: str           # must exist in taxonomy (referential contract)
    confidence: float       # 0.0-1.0 (LLM self-reported or embedding-derived)
    reasoning: str | None   # optional chain-of-thought

    @field_validator("category")
    def must_be_valid_taxonomy_node(cls, v):
        if v not in TAXONOMY_NODES:
            raise ValueError(f"Unknown taxonomy node: {v}")
        return v
```

#### Cost & Latency Contracts

| Metric | Contract | Action on breach |
|--------|----------|-----------------|
| **Cost per item** | Project-defined per-item budget | Batch more aggressively / switch model |
| **Cost per run** | Project-defined total budget | Halt if budget exceeded |
| **Latency per item** | Project-defined latency budget | Increase concurrency or switch model |
| **Total run time** | Project-defined batch deadline | Profile bottleneck tier |
| **Token usage** | Track input + output tokens per run | Alert on configured increase from baseline |

#### Reliability Contracts

| Pattern | Implementation |
|---------|---------------|
| **Retry with backoff** | Transient API errors (429, 500, 503): retry 3x with exponential backoff |
| **Fallback model** | Use only an explicitly qualified alternate model with a degraded-quality flag |
| **Rate limiting** | Respect provider rate limits; ThreadPoolExecutor with bounded concurrency |
| **Timeout** | Per-request timeout (30s); per-batch timeout (10min) |
| **Determinism caveat** | LLM outputs are non-deterministic; eval must account for variance |

### Embedding Contracts

| Contract | Rule |
|----------|------|
| **Model version pinning** | Document the selected embedding model version; model change = re-embed all |
| **Dimension stability** | Output dimension is invariant; assert before any vector operation |
| **Caching** | Embeddings are expensive; cache by content-hash; invalidate on source change |
| **Batch efficiency** | Batch embedding calls (not one-by-one); document optimal batch size |
| **Storage format** | Parquet with fixed-size-list column; DVC-tracked for large datasets |

### Training Contracts (Classical ML)

| Contract | Rule |
|----------|------|
| **Train/test split** | Fixed seed, documented split ratio, stratified if class-imbalanced |
| **Hyperparameter bounds** | Document search space and selection criterion |
| **Convergence** | Training must converge (loss decreasing); alert on non-convergence |
| **Artifact versioning** | Model artifacts DVC-tracked; metadata includes git SHA + data version |
| **Retraining trigger** | Drift exceeds threshold OR new GT available OR schema change |

---

## Rules (ML / AI)

- Every model/classifier has an eval gate: metric ≥ threshold, tested on versioned GT set
- LLM prompt changes are model version changes — require eval before deployment
- Confidence scores use embedding proximity (cosine to centroid), NOT LLM self-reported confidence
- Tiered architectures assign items deterministically; document tier-assignment logic explicitly
- Cost estimation (dry-run mode) is mandatory for LLM-calling pipelines before full execution
- Feature contracts assert dimension, dtype, normalization, and staleness before computation
- Drift detection runs on every batch; baseline is pinned to last eval run
- Reproducibility: data version (DVC) + code version (git SHA) + seed + deps (lock file) documented per model
- Ground-truth sets are versioned, reviewed by humans, and never used for training
- LLM response validation uses Pydantic structured output; malformed responses are rejected (not silently ignored)
- Embedding model changes require full re-embedding — no mixing vectors from different models
- ThreadPoolExecutor concurrency bounded by API rate limits; document max workers per provider
- Fallback models have a degraded-quality flag propagated to downstream consumers
- ADRs required for: model architecture changes, provider switches, threshold re-calibration, taxonomy evolution

---

## Worked Example: Synthetic Text Classification

This example describes a generic design, not a deployed model, dataset or budget.
Actual identifiers, thresholds, dataset sizes and provider selections remain in
project-owned private records.

```
# Domain (Phase 1)
Input: synthetic labeled text records
Labels: example category set with versioned definitions
Tiers: inexpensive classifier, embedding comparison, qualified language model
Features: selected model and dimension declared by a versioned feature contract
Ground truth: held-out, human-reviewed labels with a recorded data version
Output: example_predictions (record_id, category, confidence, tier)

# Contracts (Phase 4)
Feature: declared dimension, float32, unit-normalized, no nulls
Thresholds: configured per tier and qualified on held-out evaluation data
Evaluation: configured macro F1, per-tier precision and regression floors
Cost: explicit per-item and per-run budgets checked before execution
Tier coverage: measured per batch against its recorded baseline
Determinism: each input assigned to exactly one tier
Drift: configured limits for feature and tier-coverage changes
Confidence: documented calibrated score; do not assume self-reports are reliable
Reproducibility: versioned model, labels, dataset, seed and dependency lock
ADR: project-owned decision describing model and tier selection
```

## Worked Example: Synthetic Document Annotation

```
# Domain (Phase 1)
Input: example document text
Model: qualified primary model with an explicitly qualified optional fallback
Output: structured evidence annotations
Topology: fan-out from one document to multiple annotations

# Contracts (Phase 4)
Input: declared token budget and explicit truncation/segmentation policy
Output: validated annotation schema with allowed categories and source references
Cost: declared per-document and per-run ceilings checked before execution
Latency: explicit per-request timeout and overall batch deadline
Reliability: bounded transient retries; qualified fallback only
Concurrency: bounded by provider quotas and local resource limits
Evaluation: versioned held-out examples and project-selected precision floor
Prompt versioning: source-tracked templates; changes require fresh evaluation
Degraded mode: fallback annotations carry an explicit provenance flag
```
