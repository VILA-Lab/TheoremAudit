# Small-resource empirical programs

Use the authorized workspace and exact run ID. Acquisition and execution are separate operations.
No operation grants network access, accepts a gated license, recruits people, uploads data, or
authorizes paid services on the user's behalf.

## Resource policy

`experiment_resources.py status` reports limits and assets. Defaults are 100 MB dataset transfer
and 500 MB model transfer per run (decimal bytes), 2 GB process-group RSS, two CPU threads, 600
seconds per experiment including pilots/retries, and 1,800 seconds across the empirical program.
Pilots have a 30-second limit. Declared outputs and logs have a 100 MB limit per execution.
Available-memory checks may lower the memory allowance. Monitoring is sampled; transient overshoots
are possible. Small file size does not guarantee small runtime memory.

For larger budgets, request explicit researcher approval, then use `configure --input POLICY.json
--approval-note "reference to the researcher's approval"`. The policy file includes all limit fields
reported by `status`. Do not self-authorize increases. Host permissions remain separate. GPUs,
neural training, new human annotation, authentication, archive extraction, and remote code execution
are not automatic capabilities. A necessary study requiring them remains blocked.

## Resources

Search for actual candidates using available web/literature tools. Do not infer worldwide dataset
unavailability from a local search. Inspect documentation, licenses, annotations, and actual fields.
Dataset cards are evidence to inspect, not guarantees of label correctness or theorem assumptions.
Model-generated labels cannot silently replace independent reference labels.

The initial acquisition backend supports public, ungated Hugging Face files at immutable commits.
Select specific CSV/TSV/JSON/JSONL/Parquet files for data and configuration/tokenizer files plus
Safetensors weights for models. No Python, pickle, or archives are fetched. Prefer small shards or
smaller datasets: requesting a row-count slice does not necessarily limit download size.

Register with `experiment_resources.py --workspace WORKSPACE --run RUN register --input RESOURCE.json`:

```json
{
  "id": "DATA-1",
  "kind": "dataset",
  "access": "public",
  "description": "Dataset and purpose in this study",
  "source_description": "Creator, original study, and annotation procedure",
  "license": "Verified license identifier or terms",
  "license_source": "URL of the inspected license",
  "revision": "<actual 40-character commit hash>",
  "files": [{
    "path": "test.csv",
    "url": "https://huggingface.co/datasets/OWNER/REPO/resolve/COMMIT/test.csv",
    "expected_bytes": 12345
  }]
}
```

Replace illustrative values with inspected metadata. `expected_sha256` is optional when supplied
by the publisher; every downloaded file is hashed. Use `acquire --id DATA-1`. Verified cached files
are reused; failed/partial transfers also consume the budget. The tool checks redirect hosts,
declared/actual sizes, supplied checksums, and dataset columns. Parquet inspection requires
`pyarrow`; choose another format or obtain dependency-install permission if it is unavailable.

For existing local data/models, use `access: "local"` and `source_path` per file instead of a URL.
Source paths are relative to the paper directory and must already exist with permission.
Registration hashes files in place and derives a content-based revision. Do not copy private data
into public artifacts. Availability does not authorize redistribution; keep provenance and loading
instructions rather than automatically including datasets/model weights in a submission package.

## Feasibility before selection

New strategies use `"schema_version": 2`. Add `preflight` to every candidate:

```json
{
  "status": "ready",
  "evidence_kind": "real_data",
  "operation": "inference",
  "resource_ids": ["DATA-1", "MODEL-1"],
  "required_columns": ["text", "label"],
  "new_human_annotation": false,
  "annotation_evidence": "Source, meaning, independence, and limitations of existing labels",
  "sampling_plan": "Prespecified splits, sample IDs/seed, group sizes, and leakage controls",
  "estimated_seconds": 120,
  "estimated_memory_mb": 800,
  "rationale": "How the actual resources and CPU budget address this claim"
}
```

Require reference labels, repeated annotations, or annotator IDs only when the particular study
needs them. Column presence does not establish statistical independence or reliable ground truth.
`evidence_kind` is `synthetic`, `semi_synthetic` (e.g. real text with injected noise), or `real_data`.
`operation` is `simulation`, `inference`, or `classical_fit`. Synthetic candidates may need no assets
or columns. `status` is `ready`, `blocked`, or `awaiting_approval`. A scientifically important but
unavailable experiment may stay selected so its missing evidence remains visible; use `mark-blocked`
with the precise reason. Missing resources do not make a claim intrinsically untestable.

`write-strategy` checks ready assets, required columns, and estimates; `propose` preserves the
preflight. Only real-data evidence may use `real_system`, and review must still assess whether it
addresses the actual application. Existing version-1 evidence is not rewritten. Version-2 strategies
cannot be downgraded; use the normal experiment-revision workflow to adopt v2 after legacy executions.

## Pilot and execution

Use `experiment_tools.py inspect-script --id EXP-1 --script experiments/study.py` and list imported
local helpers with `--dependency`. Use local model paths with `local_files_only=True`,
`trust_remote_code=False`, and explicit CPU placement. Installed dependencies must be checked first.

Execute with `experiment_tools.py --workspace WORKSPACE --run RUN run-inspected --id EXP-1
--input EXECUTION.json`. Example input for a script accepting these particular arguments:

```json
{
  "pilot": true,
  "arguments": ["--samples", "20", "--output", "experiments/results/pilot-1.json"],
  "output_paths": ["experiments/results/pilot-1.json"]
}
```

Inspect pilot logs and measured memory/time, then use `pilot: false` with the planned sample size
and fresh output paths. A successful pilot is not evidence of statistical adequacy and cannot be
evaluated as the scientific experiment. Changing code, dependencies, or assets requires another
pilot. Runtime is cumulative across retries. Only one resource/execution operation runs per run.

The runner preserves receipts, logs, output hashes, resources, budgets, peak sampled RSS, and
failures. It uses static inspection, offline-library settings, and Python socket guards. These are
not an OS sandbox for malicious/native code; normal host security controls still apply. There is
no arbitrary shell command endpoint. Manual `record-execution` remains for legacy programs only;
v2 evidence must match a managed receipt. The web interface displays checking, downloading,
running, awaiting-approval, blocked, and interrupted resource-operation states.

Resource failures never change accepted mathematics. Continue a restricted manuscript only when
the existing route explicitly permits incomplete evidence; preserve its submission restrictions.
