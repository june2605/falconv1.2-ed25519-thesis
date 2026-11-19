# Phase 5.2A — Benchmark methodology

The pilot measures the Ed25519 and Falcon-512 primitive APIs, the actual
HybridSign PDF pipeline, and public storage sizes. The worktree started
clean on `thesis/ui-demo` at `7314f4c`. Production signature semantics,
wire formats, vault, native bridge and the release artifacts were kept
at that baseline. The benchmark and chart scripts run separately from
the desktop.
[Harness](../research/benchmarks/phase5_2a.py) ·
[Phase 5.1 protocol](phase5-1-experiment-gap-analysis.md#phase-52-protocol) ·
[Pilot results](phase5-2a-pilot-analysis.md)

## Workloads and trial design

- **A — Primitive calls.** For each block, generate one deterministic
  public buffer for each size, 64 and 1,024 bytes. Both algorithms receive
  the very same bytes object for that size. `prepare_public_message` is
  timed separately. The harness applies no prehash to the primitive input.
  Each algorithm generates fresh random key material per trial. Keygen,
  sign and positive verify each have separate `perf_counter_ns()` clocks.
  Key length checks and modified-message rejection are outside those
  clocks. Ed25519 signs via PyNaCl `SigningKey.sign()`, including its
  internal hashing and Python binding. Falcon uses the pinned
  `falcon_512` detached binding with its own internal hashing and
  signing randomness. The calls measure the library APIs, including their
  wrapper/copy costs. [Primitive trial](../research/benchmarks/phase5_2a.py#L156)
- **B — Actual PDF pipeline.** Use the native Python application's
  `sign_with_key_material()` on the public demo sample and exact 1 MiB and
  10 MiB fixtures. The `unprofiled` and `profiled` modes use distinct
  signing trials with the same workload schedule. Reuse one freshly
  generated hybrid signing pair in memory for this part. One independently
  generated wrong public pair is used for negative controls. No vault,
  password, GUI or signing API replacement is used.
  [PDF trial](../research/benchmarks/phase5_2a.py#L222)
- **C — Size observations.** Record primitive public/private lengths and
  actual detached signature lengths. Record both detached signature lengths
  from the published hybrid PDF, its two message lengths, final file
  size and growth over the exact source. Ed25519 private size means its
  32-byte seed encoding. These rows measure byte counts. The protocol
  produces no artificial single-layer PDF formats.
- **Scheduling.** One sequential process runs three recorded warm-up
  blocks, then 30 measured blocks. Each block processes the two primitive
  sizes and the three PDFs in both pipeline modes. It alternates which
  primitive goes first, rotates the PDF size order and alternates the
  first PDF mode within each size. Primitive work precedes PDF work in
  each block. Crypto randomness remains under the installed libraries.
  The file cache is not cleared. Observations describe repeatedly used
  public inputs on the observed host and filesystem.
  [Schedule](../research/benchmarks/phase5_2a.py#L348)

The larger PDFs derive from the 742-byte public sample. The generator
inserts bounded PDF comment lines before the xref table and updates
`startxref`, preserving the original objects and visible content. It checks
exact length, the controlled header and EOF, xref object offsets, stream
length, the expected public text and reserved-marker policy. It repeats
the checks on bytes read back from disk. These checks cover this fixture
profile. They are not a general PDF conformance checker.
[Generator and fixture checks](../research/benchmarks/phase5_2a.py#L77) ·
[Sample provenance](../demo_assets/README.md)

## Timing boundaries

| Metric | Measured window |
| --- | --- |
| `sign_and_publish` | A high-resolution wall clock around the unprofiled public memory-key signing call. Includes source capture and checks, in-memory key validation, the two revisions, transaction I/O, candidate self-verification, path checks and atomic publication. Excludes benchmark fixture setup, initial hybrid key generation, external postpublication verification and cleanup after the benchmark checks. |
| `verify_published_file` | A separate unprofiled high-resolution clock around `verify_file_with_public_keys()` on the just-published file. Includes reading it, strict parsing and both native checks. Excludes the negative controls and metadata collection. |
| Profiled sub-operations | Temporary wrappers observe calls to the real signer in the benchmark process. They clock source capture, each placeholder, Ed25519 message assembly and native signing, the first embedding, Falcon's SHAKE256-64 prehash and native signing, final embedding, candidate write/fsync, candidate self-verification and publication. The harness checks that the exact expected call sequence ran. Each callable retains the production behavior. |
| `profiled_sign_and_publish` | A separate wall clock for the instrumented trial. Instrumentation adds overhead. The profiled sub-operations are selected windows and omit intermediate work including some parsing, key checks and stage writes. Use the unprofiled result as the end-to-end reference. |
| `sign_slot_*` and `verify_slot_*` | Ten original timing slots from each 11-element result, recorded as legacy seconds. The first tuple item remains the output path or verification Boolean. Inherited `time.time()` timings cover narrower or different scopes from the two independently measured wall clocks. The Ed25519 slot named `hash` times raw slice assembly rather than a SHA-512 prehash. |

For the PDF pipeline, the Ed25519 message is the concatenation of its
first-revision ByteRange intervals. Falcon receives the application-level
64-byte SHAKE256 digest of its covered bytes, including the full Ed25519
container. The primitive comparison instead presents both algorithms
with the same raw buffer. These two timing contexts answer different
questions. [Protocol source](../sign.py#L74) ·
[Message helpers](../utils.py#L267) ·
[Profile wrappers](../research/benchmarks/phase5_2a.py#L184)

Every measured or warm-up signing trial is verified. The hybrid signer
requires its staged self-check, followed by a separately witnessed positive
verification after publication. The harness also checks rejection of a
covered-text edit and mismatch with the other public-key pair, outside the
positive clocks. Primitive verification requires matching-key acceptance
and modified-message rejection. These checks cover the tested inputs.
The Phase 5.1A source-level canonicalization gap in the outer Falcon
container remains open. The pilot supports neither whole-file
byte-uniqueness nor CMS/PAdES compatibility.
[Integrity audit](phase5-1a-signature-integrity-audit.md)

## Output, validation and stop conditions

The run uses an exclusively created directory beneath the caller's existing
local output root. The harness rejects repository and worktree roots and
descendants. It keeps generated public PDFs there and removes the owned
per-trial signed output after its observations. Keys and signature bytes
are held in memory. Reports contain timing and size values, public
input hashes, process-level environment metadata and sanitized failure
codes. They do not contain key bytes, signature bytes, credentials or
full exception payloads.

| File | Contents |
| --- | --- |
| `experiment.json` | Experiment UUID, status, UTC start/end, commit and worktree status, versioned harness/source hashes, environment including CPU/OS/libraries/native Falcon provenance, and fixture sizes/hashes |
| `raw.csv` | Experiment reference, category, mode, algorithm, operation, workload and bytes, warm-up/measured phase, repetition/order and outcome. `elapsed_ns`, `legacy_seconds` and `observed_bytes` are kept in separate columns. Hardware and software are joined through the experiment ID. |
| `summary.json` | Count, arithmetic mean, median, sample SD, min, max and inclusive linearly interpolated P95 by matching category, mode, workload, algorithm, operation and unit. P95 requires at least 30 successful measured observations. |
| PNG charts | Separate median comparisons for 64-byte primitive calls (microseconds) and the actual unprofiled hybrid PDF workflow (milliseconds), generated with Windows .NET Charting. |

The summary uses every successful measured row, including slow trials.
Warm-ups stay in the raw data and are excluded from measured statistics.
An unexpected failure stops the run, marks the current trial's rows failed,
writes a failure reason and updates the manifest. A reached time budget
records an exclusion at the next trial-admission boundary. This does not
interrupt a native operation in progress. A failed run retains its raw
record, when opened, and has no completed summary.

The startup check requires the known native Falcon binary, unchanged
production cryptographic sources, adequate initial available RAM and
output disk space. RAM reserve is at least 512 MiB and 48 times the
largest selected input. Disk reserve is ten times the largest input
plus the total generated fixture sizes and 64 MiB. The default is the
public sample plus 1 and 10 MiB. The optional 40 MiB condition is
explicit opt-in and remains subject to preflight. The command has no
200 or 500 MiB mode. The desktop 50 MiB input limit is preserved,
and historical size labels do not drive new input generation.

## Reproduce the pilot

Run from the repository root using the existing Windows `.venv`. Keep
unrelated workloads quiet during collection. Pass an existing trusted
folder on local NTFS outside Git and retain the printed run directory.

```powershell
.\.venv\Scripts\python.exe -B -m research.benchmarks.phase5_2a `
  --output-root (Join-Path $env:LOCALAPPDATA 'Temp') `
  --pdf-mib 1 10 --warmups 3 --repetitions 30 --budget-seconds 300

.\research\benchmarks\phase5_2a_charts.ps1 -RunDirectory '<printed run directory>'
```

The script needs no new dependency on the validated host. It reuses the
installed cryptographic libraries. The chart script reads the completed
summary and creates new chart files without replacing existing files.
Reproduction fixes input bytes, code, methodology and conditions as
recorded. Timing values and randomized cryptographic output can vary.
Historical CSVs and PDF datasets are checked separately against Phase 1
and never become inputs or observations of this pilot.
[Phase 1 manifest](phase1-baseline.json) · [Historical methodology audit](phase5-1-experiment-gap-analysis.md)
