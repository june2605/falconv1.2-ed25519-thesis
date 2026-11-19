# Phase 5.1 — Historical experiments, evidence gaps and Phase 5.2 protocol

The three evidence classes used here are **A**, inherited FALCON/eSign
measurements, **B**, functional checks of the current code and desktop
release, and **C**, independent experiments proposed for Phase 5.2.
The tables in this document are a read-only analysis of A. No timing in
them was collected by running the current application or a new benchmark.

## A — Inherited artifacts and provenance

All 15 paths in the Phase 1 SHA-256 manifest are present under
`D:\Final_Thesis`. All hashes matched through streaming reads. There are ten
CSV files and five materialized PDFs. The CSVs were added together by commit
`7f199dd3bc89b4dd2e2c5f3f71dc4751a3c87f01` dated 25 June 2026. The
`data_test/` Git LFS records were added in `8ca8b14`. All five pointer
SHA-256 values and sizes match the materialized PDFs. Each CSV's contents
also match the original commit after accounting for the Windows CRLF
checkout. The Phase 1 hashes cover the untouched local checkout bytes. Each sign and verify CSV has unique consecutive run labels
1–100 and exactly 100 records. The observed PDFs are the preserved
same-labelled inputs. There is no per-row input hash recording which
individual bytes were used in the original capture.
[Phase 1 manifest](phase1-baseline.json) ·
[Original benchmark commit](https://github.com/luluon-cyper/FALCON/commit/7f199dd3bc89b4dd2e2c5f3f71dc4751a3c87f01) ·
[Input dataset commit](https://github.com/luluon-cyper/FALCON/commit/8ca8b14)

The labels below are file stem suffixes. Exact size is from the PDF on disk.
Each row corresponds to `benchmark/sign_benchmark_<label>.csv`,
`benchmark/verify_benchmark_<label>.csv` and `data_test/file_test_<label>.pdf`.

| Label | Actual PDF bytes | MiB | Signing rows | Verification rows | `ok=True` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1mb` | 1,048,576 | 1.000 | 100 | 100 | 100 |
| `10mb` | 10,485,760 | 10.000 | 100 | 100 | 100 |
| `50mb` | 55,715,200 | 53.134 | 100 | 100 | 100 |
| `200mb` | 209,715,200 | 200.000 | 100 | 100 | 100 |
| `500mb` | 509,715,200 | 486.102 | 100 | 100 | 100 |

The inherited `demo.py` at the benchmark commit selects `file_test_500mb.pdf`
and runs 100 iterations. The later inherited `0f3b513` copy selects
`file_test_1mb.pdf`. The benchmark-commit version writes to `bechmark/`,
while checked-in files reside in `benchmark/`. These snapshots document
a method but do not provide a run manifest and an exact invocation for
each size. The original driver generates a new pair per iteration, signs
using both algorithms, verifies the output under that pair and logs the
overall `ok`. It times `generate_keys()` with `perf_counter()`, including
historical plaintext key-file writes. `sign.py` and `verify.py` derive
their stage fields from `time.time()` differences, in seconds. The
`ed_hash` field covers collecting/joining bytes in the inherited helper
despite its name. `fal_hash` covers construction of the SHAKE256 message.
In the historical signer, preparation/readback and embedding writes can
be in different fields from cryptographic calls. The combined stage sum
is not elapsed UI/MSI/EXE latency or a current signed-PDF transaction time.
[Benchmark driver snapshot](https://github.com/luluon-cyper/FALCON/blob/7f199dd3bc89b4dd2e2c5f3f71dc4751a3c87f01/demo.py) ·
[Historical signer](https://github.com/luluon-cyper/FALCON/blob/7f199dd3bc89b4dd2e2c5f3f71dc4751a3c87f01/sign.py) ·
[Historical verifier](https://github.com/luluon-cyper/FALCON/blob/7f199dd3bc89b4dd2e2c5f3f71dc4751a3c87f01/verify.py) ·
[Current timing contract](phase2b4b2-regression.md)

The archived CSVs do not record CPU, RAM, storage, timer resolution, OS
build, Python/native library versions, run order across sizes, cache
state, warm-ups, seeds or per-trial input and key fingerprints. The old
requirements are unpinned. Its README describes supported environments.
The later Phase 1 environment records observed Windows/Python/dependency
versions in November 2026 and cannot identify the June CSV machine.
The historical driver records no deterministic RNG policy and uses fresh
keys. Falcon signing has native randomness and Ed25519 signatures are
deterministic for fixed material and message. No historical standalone
Ed25519-only or Falcon-only runs, peak memory, CPU, actual detached
signature lengths, output-size logs, invalid-case trials, signed corpus
or raw timestamp traces were located. The inherited `esign_test.zip`
directory lists Python and image assets. No missing member of the 15-item
benchmark manifest was inferred from any other file. The provenance does
not establish that all runs used identical source or dependencies across
labels. [Historical requirements](https://github.com/luluon-cyper/FALCON/blob/7f199dd3bc89b4dd2e2c5f3f71dc4751a3c87f01/requirements.txt) ·
[Historical Phase 1 environment record](phase1-baseline.json)

### Descriptive statistics

Calculations use every row, including zero measurements and slow trials.
Inputs were parsed as numeric seconds and converted to milliseconds
after aggregation. The mean is arithmetic. The median is the sample median.
SD is the **sample** standard deviation (denominator `n-1`). P95 uses
inclusive linear interpolation (rank `1 + 0.95 × (n−1)`, Hyndman–Fan type 7).
Values are rounded to two decimals only for display. For each run, the
signing measure is `ed_total + fal_total` excluding `keygen_total`. The
verify measure is the stored `total`. Sign stage sums and verify component
sums were checked against their stored totals to within 1 ns absolute or
`1e-9` relative tolerance. All fields parsed, all values were finite and
nonnegative and all checked sums agreed. `True` is the reported historical
overall Boolean for the normal inputs. Its frequency does not estimate
either false acceptance under adversarial inputs or performance of the strict
current verifier.

**Signing stage sum (ms)**

| Label (MB suffix) | Mean | Median | Sample SD | Min | Max | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 83.67 | 83.77 | 6.02 | 67.68 | 100.75 | 94.09 |
| 10 | 285.95 | 270.30 | 42.79 | 253.13 | 448.98 | 391.97 |
| 50 | 1265.91 | 1228.09 | 118.89 | 1156.44 | 1934.82 | 1455.11 |
| 200 | 4860.05 | 4653.20 | 530.66 | 4433.33 | 7312.14 | 5606.17 |
| 500 | 11666.55 | 11331.84 | 998.98 | 10945.88 | 18775.66 | 12994.49 |

**Stored verification total (ms)**

| Label (MB suffix) | Mean | Median | Sample SD | Min | Max | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 25.10 | 25.90 | 5.90 | 14.30 | 41.13 | 34.23 |
| 10 | 97.92 | 92.82 | 19.16 | 76.92 | 183.46 | 140.80 |
| 50 | 399.11 | 387.73 | 46.52 | 368.16 | 731.24 | 434.51 |
| 200 | 1453.86 | 1409.56 | 195.41 | 1379.39 | 2495.44 | 1517.60 |
| 500 | 3434.77 | 3400.96 | 233.51 | 3353.78 | 5691.54 | 3550.19 |

**Stored combined keygen total (ms)**

| Label (MB suffix) | Mean | Median | Sample SD | Min | Max | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 17.79 | 15.88 | 5.76 | 12.13 | 43.97 | 29.41 |
| 10 | 20.45 | 17.58 | 7.99 | 12.56 | 53.65 | 37.38 |
| 50 | 18.42 | 17.19 | 5.00 | 12.28 | 41.69 | 27.44 |
| 200 | 19.09 | 16.49 | 6.95 | 12.42 | 46.64 | 33.52 |
| 500 | 19.42 | 17.51 | 6.12 | 12.50 | 48.07 | 30.11 |

**Mean decomposition and one clock-resolution symptom**

| Label | Sign Ed stage (ms) | Sign Falcon stage (ms) | Verify Ed stage (ms) | Verify Falcon stage (ms) | Verify I/O (ms) | Zero-valued Falcon verify crypto field |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 34.05 | 49.62 | 5.18 | 2.53 | 17.39 | 97/100 |
| 10 | 150.94 | 135.01 | 41.14 | 33.24 | 23.54 | 92/100 |
| 50 | 708.14 | 557.78 | 205.84 | 158.36 | 34.91 | 95/100 |
| 200 | 2743.99 | 2116.05 | 765.72 | 593.59 | 94.55 | 96/100 |
| 500 | 6670.60 | 4995.96 | 1821.88 | 1400.49 | 212.40 | 97/100 |

The tiny Falcon verification sub-operation often records zero
(92–97/100 per size). This is consistent with a sub-operation falling
below the timing resolution of the historical stage clock. The timer
tick and hardware are unrecorded. Zero readings cannot be interpreted as
zero compute cost or used to support a precise Ed25519-to-Falcon speed
ratio. Large differences in totals are consistent with processing more PDF
bytes. Changes in parsing, allocation, hashing and I/O all contribute, and
this observational dataset cannot isolate their causal effects.

## B — Existing functional and format evidence

The two fixed Phase 1 pairs, strict parser and vault tests, and current
desktop evidence cover tested positive/negative document and key
conditions. Phase 4C.3 reports 1,666 pytest passes and eight existing
Windows symlink skips, 266 Playwright passes and a portable acceptance
replay. Phase 5.1 refreshed a targeted 748-test subset. These evidence sets
answer correctness questions. Neither suite has a workload or sampling
plan for latency claims. Prior short Argon2id probes are scoped to their
own local functional validation.
[Phase 4C.3](phase4c3-final-release-review.md) · [Phase 5.1 validation](phase5-1-research-audit.md#validation-and-remaining-academic-decisions) ·
[Phase 3 vault probes](phase3-2b1-regression.md#dependency-and-runtime-validation)

Current raw sizes are independently auditable from code and native APIs.
Public keys are 32 + 897 = **929 bytes** for the hybrid tuple. Stored
private payload values are 32 + 1,281 = **1,313 bytes** before private
payload metadata. Native detached signatures are 64 bytes for Ed25519
and variable up to 752 bytes for the Falcon binding. The default
hybrid PDF adds **4,626 bytes**, a deterministic container cost with
the configured capacities, distinct from the native signature sizes.
The encrypted vault is **2,416 bytes**, including header and tag.
Standalone application PDF outputs and native Falcon sig-size
distributions still require measurement or explicit experimental
profiles. The desktop signing ceiling is **50 MiB** and its read-only
verification ceiling adds **65,536 bytes** for signed overhead. The
preserved `50mb`, `200mb` and `500mb` source PDFs exceed the
desktop signing ceiling. These inputs appear only in the inherited-data analysis here. [Format accounting](phase5-1-implementation-evidence.md#pdf-preparation-and-signed-revisions) ·
[Desktop size limits](../desktop/pdf_io.py#L15)

## Phase 5.2 protocol

### Questions and comparison boundaries

Define independent observables for primitives, the PDF processing pipeline
and product overhead. Use public synthetic inputs for new runs. Keep the
native algorithms, dependency pins, signed messages and production format
fixed. No Phase 5.2 harness, instrumentation or heavy benchmark is
implemented in this phase.

| Comparison | Proposed measurement | What it would support |
| --- | --- | --- |
| Primitive API only | Generate Ed25519 with PyNaCl and Falcon-512 with the same `falcon_512` binding in memory. Measure keygen for each, sign and verify both on identical raw byte inputs (at least 64 B and 1 KiB) and log raw sizes. A second small, clearly separate sweep may assess message length. Prepare messages, import libraries and load verify fixtures outside the timed part. | Comparable single-primitive API costs under the observed machine and dependency set. These timings do not include PDF stages, vault KDF, disk, or self-verification. |
| Application-defined messages | Use the same synthetic PDF revision bytes as the product. Time preparation/concatenation, SHAKE256-64 and native calls separately for the two actual messages. Measure real hybrid keypair generation both including its validation/self-tests and at the constituent calls. Record verification of the bare APIs separately from structural validation. | Explains the inner layer's dependence on PDF bytes and the outer native call's fixed-length digest input. Avoid a misleading direct comparison between the Falcon call on a digest and Ed25519 on a much larger message. |
| Whole-file hybrid | Use the existing `sign_with_key_material()` transaction and actual `verify_bytes()` or `verify_file_with_public_keys()`. Explicitly distinguish memory verify from file verify. Capture publication, prepublication self-verification and staging as part of the signing wall-clock measurement. Exclude interactive picker time. Measure vault unlock and desktop/service overhead in separate scenario rows only if instrumented. | Real end-to-end hybrid PDF overhead of this strict profile. Prior stage tuple totals alone are insufficient. |
| Whole-file single-layer comparators, if approved | Use an isolated research harness and declare a comparator profile for an Ed-only and a Falcon-only signature over the same input PDF. Use the same algorithm-specific message transformations as the corresponding stages, but without the other container. Use equivalent snapshot, candidate, flush, self-verify and publish boundaries for I/O comparisons. Detect covered modification and wrong keys with each comparator's matching verifier. Record output sizes separately. | Comparable one-layer workflow baselines. Production accepts a complete pair only. A hypothetical, harness-only one-container/control would require its own test adapter and explicit format description. A minimal thesis can report raw/stage comparisons and the real hybrid pipeline while leaving one-layer PDF timings unmeasured. |

Independently checking the nested design is a separate correctness
experiment. Before measuring, apply a preregistered matrix on fresh matched
keys and independent controls. Include valid pairs, content modification,
wrong and mixed key pairs, removal/reordering of either layer, trailing
bytes, truncation, noncanonical metadata/padding and the native
encoding-equivalence question identified by source review. List expected
outcomes and distinguish structurally rejected inputs, a mathematical
rejection, and an I/O or setup failure. Test the application and
single-layer comparison adapters only according to their own advertised
profiles. Count failures and keep cases that challenge the initial
hypothesis. This assesses tested behavior with fixed trusted test keys.

### Inputs, environment and scheduling

1. Use a deterministic synthetic PDF generator with parameterized
   stream length, a valid xref/trailer and a documented seed/version
   (or a specified repeated byte pattern). Vary only the intended
   stream padding or controlled corpus seed. Record exact byte lengths
   and SHA-256. Include a small fixture at demo scale and target 1,
   10 and 50 MiB (binary units), adjusting framing so the 50 MiB
   fixture is actually within the desktop limit. Validate artifacts
   before measurement. If resources and project scope later justify
   200 or 500 MiB, run separate core-only experiments with recorded
   safe memory/disk budgets and mark the GUI path ineligible.
2. Record Git SHA and clean status, generator revision/seed, environment
   manifest, CPU model, architecture, logical/physical cores, RAM,
   storage/filesystem, OS build and Python version. Record the exact
   Falcon wheel/native digest, PyNaCl/libsodium release, cryptography
   and OpenSSL versions if a vault scenario is included. Record power
   settings, free space, background load and warm-cache/cold-start
   conditions. Use a controlled local disposable output directory.
   Never persist actual private keys, generated passwords or RNG state.
3. Run a separately labelled pilot to choose loop/batch sizes and confirm
   enough resolution and headroom. As a starting protocol, use three
   fresh process sessions with five explicit untimed warm-up blocks per
   condition and 30 measured trials per session (90 per condition).
   Publish any pilot-driven adjustment before collecting confirmatory
   samples. Alternate conditions within seeded, balanced blocks over the
   same inputs. Pair comparisons by block and separate cold-start from
   warmed measurements. If tiny calls need batching, record iteration
   count and divide aggregate elapsed time for the per-call estimate.
   Do not reduce native randomness or patch production entropy to make
   signatures bit-identical. Use the seed for fixtures and run order only.
4. Measure wall time with monotonic `perf_counter_ns()`, and process
   CPU time with `process_time_ns()`. Expose CPU ms and report average
   core equivalents from CPU time divided by wall time if used. A
   multi-threaded operation may exceed one core equivalent. Record
   process-private and resident memory separately where available. Use
   Windows process accounting or a documented native-aware tool for
   peak working set, with a fresh process and a baseline for each
   relevant condition. A Python allocation tracer alone omits native
   buffers and runtime memory. Avoid measuring instrumentation-induced
   overhead as crypto time. Define phase boundaries, calibrate the data
   collector and report clock resolution.
5. Log one raw row per trial with condition, input identity and size,
   operation, key-use policy (fresh per generation trial, controlled
   reuse for timed sign/verify where appropriate), session/block,
   warm-up flag, operation durations and units, peak-memory method,
   exact raw signature and output lengths and result/error status.
   Preserve failed or interrupted trials with reason. Include actual
   completed trial counts and denominators. Write raw outputs outside
   the source repository and record the manifest and hashes with the
   thesis results. Store only public identifiers and metadata. Do not
   write decrypted material.
6. Report mean, median, sample SD, min/max and inclusive P95 with sample
   counts. Show distribution/paired ratios and absolute costs, with
   uncertainty across sessions. For uncertainty intervals state the
   resampling unit (such as process/session blocks) and limit
   generalization with only three sessions. Report any protocol exclusion
   in advance and preserve the underlying rows. Never trim slow trials
   silently. Report missing methods/unsupported sizes and keep the
   historical series separate in all tables and figures.

The implementation work for these experiments is research instrumentation,
input generation, logging and, if chosen, isolated single-layer adapters. A
standalone KAT harness is a different task from the timing comparison.
Acceptance for a publishable experimental result requires independently
auditable input/output hashes, positive and negative controls for each
selected profile, raw observations that reproduce the published table,
a fixed analysis plan and a complete record of exceptions and measurement
boundaries. A result lacking comparable single-layer workflows should
claim only the measurements actually made.
