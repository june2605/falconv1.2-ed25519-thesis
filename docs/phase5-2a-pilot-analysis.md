# Phase 5.2A — Controlled pilot analysis

**Outcome.** Pilot `b1053ba0-598b-4bb8-9bec-1fcdab9694db` completed on
19 November 2026. It ran 30 measured and three warm-up blocks on one
Windows host. There were **360 measured trials, 36 warm-up trials, zero
failed trials and zero exclusions**. Trial counts include preparation
and separate profiled/unprofiled PDF work. The raw CSV contains 5,910
measured and 591 warm-up rows. The 197 summary series each use 30 measured
observations. Signing verification and the required negative controls
succeeded throughout. This is exploratory evidence for the specified
inputs and host. [Full methodology](phase5-2a-benchmark-methodology.md)

## Run identity and environment

| Item | Observed value |
| --- | --- |
| Baseline | `thesis/ui-demo` at `7314f4c94fd1402e9336322a056e055fa7799753` |
| Worktree | Clean at the start of the phase. The pilot manifest records dirty status during collection because the new research files were uncommitted. The production source check passed. |
| Harness | Version `1.0.0`, SHA-256 `29a697ca3d4063773e3be9856a9a3e70fba7d4671e37c89613d0fc775a579410` |
| Hardware | Intel Core i7-10850H at nominal 2.70 GHz, 12 logical processors, 16,762,388,480 reported physical RAM bytes |
| Windows and storage | Windows 11 Pro AMD64 build `26200.9974`, local C: NTFS output. Initial available RAM 7,431,409,664 B and free output space 18,684,575,744 B. |
| Software | CPython 3.11.9, PyNaCl 1.6.2, pqcrypto 0.3.4, cryptography 50.0.2 installed |
| Falcon | `falcon_512` PQClean clean, pinned revision `2cc64716044832eea747234ddbffc06746ab815d`, native hash `ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237` |
| Collection conditions | One sequential process, no cache reset, reported perf-counter resolution 100 ns, 300 s admission ceiling, 41.17 s from manifest start through summary. CPU frequency, allocator state and physical I/O timing were not controlled. |

The primitive controls were identical 64-byte and 1,024-byte deterministic
buffers. The PDFs were the 742-byte public sample, 1,048,576-byte exact
fixture and 10,485,760-byte exact fixture. Their hashes and both primitive
message hashes appear in `experiment.json`. No 40 MiB or historical
200/500 MB workload ran. No per-operation peak RAM or CPU utilization
measurements were collected.
[Falcon provenance and limits](phase5-1-research-audit.md#falcon-implementation-and-version-boundaries)

## A — Primitive APIs

Elapsed time is in **microseconds**. Key generation is grouped by the
associated message workload, although no message is an input to key
generation. Sign and verify used the same raw message for each algorithm
at each size. The underlying implementations still perform their own
algorithm-specific processing.

| Buffer | Algorithm | Operation | n | Mean | Median | Sample SD | Min | Max | P95 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 64 B | Ed25519 | keygen | 30 | 50.56 | 45.45 | 16.47 | 39.40 | 116.00 | 80.61 |
| 64 B | Ed25519 | sign | 30 | 38.22 | 36.75 | 6.76 | 34.80 | 72.20 | 44.16 |
| 64 B | Ed25519 | verify | 30 | 91.06 | 89.80 | 6.15 | 86.70 | 120.00 | 98.56 |
| 64 B | Falcon-512 | keygen | 30 | 13792.59 | 12026.45 | 3792.15 | 9921.80 | 26511.30 | 19121.44 |
| 64 B | Falcon-512 | sign | 30 | 4296.11 | 4230.05 | 137.54 | 4115.90 | 4694.60 | 4548.64 |
| 64 B | Falcon-512 | verify | 30 | 44.81 | 44.05 | 4.03 | 42.90 | 65.90 | 45.73 |
| 1024 B | Ed25519 | keygen | 30 | 38.47 | 38.05 | 2.62 | 35.10 | 47.80 | 43.70 |
| 1024 B | Ed25519 | sign | 30 | 39.87 | 39.10 | 4.07 | 37.70 | 60.70 | 41.84 |
| 1024 B | Ed25519 | verify | 30 | 95.76 | 91.45 | 13.12 | 89.40 | 141.40 | 127.97 |
| 1024 B | Falcon-512 | keygen | 30 | 14045.07 | 13159.95 | 3934.54 | 9780.50 | 22175.40 | 21912.31 |
| 1024 B | Falcon-512 | sign | 30 | 4279.34 | 4246.20 | 87.92 | 4166.30 | 4511.40 | 4424.36 |
| 1024 B | Falcon-512 | verify | 30 | 49.50 | 47.80 | 5.32 | 47.00 | 69.30 | 62.70 |

On the 64-byte buffer, Ed25519 signing had a 36.75 µs median and
Falcon-512 signing had a 4,230.05 µs median. Median verification was
89.80 µs for Ed25519 and 44.05 µs for Falcon in this run. These compare
the installed APIs at the stated boundaries. They do not rank the
algorithms across hardware, calling interfaces or workloads. Public buffer
preparation is a distinct series in the output.

## B — Actual hybrid PDF pipeline

Unprofiled wall times are in **milliseconds**. The published-file check
includes PDF I/O and both signature layers. There are independent groups
for sign/publish and external verification, both collected for each
unprofiled signing trial.

| Input PDF | Operation | n | Mean | Median | Sample SD | Min | Max | P95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 742 B | Sign and publish | 30 | 26.313 | 23.582 | 11.344 | 22.026 | 85.130 | 30.949 |
| 742 B | Verify published file | 30 | 0.397 | 0.381 | 0.043 | 0.351 | 0.523 | 0.510 |
| 1 MiB | Sign and publish | 30 | 50.577 | 47.268 | 15.909 | 44.856 | 134.018 | 53.864 |
| 1 MiB | Verify published file | 30 | 7.723 | 7.683 | 0.305 | 7.354 | 9.114 | 8.054 |
| 10 MiB | Sign and publish | 30 | 258.546 | 250.952 | 35.217 | 244.078 | 442.709 | 265.693 |
| 10 MiB | Verify published file | 30 | 72.617 | 72.020 | 3.052 | 70.892 | 88.413 | 73.670 |

For comparison with internal accounting only, the medians of the
per-trial sums of the two **legacy signing stage total slots** were
**8.726 ms**, **22.624 ms** and **145.613 ms**, respectively. The observed
end-to-end medians were **23.582 ms**, **47.268 ms** and **250.952 ms**.
The subtotal omits parts of the transaction and uses a different clock.
The gap cannot be attributed to any one component. The 10 MiB signing
maximum was 442.709 ms and remains included in the data and the summary.
The cause of longer observations was not isolated.

### Profiled pipeline stages

The table gives medians in **milliseconds** from separate instrumented
trials. Each cell has 30 observations. Sub-operation medians are not
added to estimate a full trial duration.

| Real production call measured | 742 B | 1 MiB | 10 MiB |
| --- | ---: | ---: | ---: |
| `capture_source` | 0.327 | 0.534 | 3.192 |
| `prepare_ed25519` | 0.012 | 0.533 | 4.571 |
| `assemble_ed25519_message` | 0.002 | 0.413 | 3.360 |
| `ed25519_sign` | 0.057 | 5.544 | 55.573 |
| `embed_ed25519` | 0.050 | 0.905 | 8.374 |
| `prepare_falcon` | 0.015 | 0.592 | 5.246 |
| `shake256_prehash` | 0.015 | 2.585 | 25.396 |
| `falcon_sign` | 4.358 | 4.278 | 4.381 |
| `embed_falcon` | 0.082 | 0.918 | 8.501 |
| `write_and_fsync_candidate` | 1.862 | 2.680 | 14.307 |
| `self_verify_candidate` | 6.955 | 14.416 | 80.808 |
| `publish_candidate` | 0.375 | 0.374 | 0.378 |

Across these three inputs, the median Falcon native signing call was
about 4.28–4.38 ms. Its input is a fixed 64-byte digest. The explicit
SHAKE256 prehash handles the growing covered PDF revision and its
median increased from 0.015 ms to 25.396 ms. Ed25519 processes raw
selected first-revision bytes, so the native signing call and the
separately clocked byte assembly have different boundaries. The
candidate self-check and the published-file verification also have
different I/O contexts. This pilot does not establish which part of
those contexts caused the observed differences.

## C — Storage sizes

The primitive controls observed 32-byte Ed25519 public keys and
32-byte private seeds, and 897-byte Falcon public and 1,281-byte
private keys. Ed25519 detached signatures were consistently 64 bytes.
Falcon detached signature lengths in the measured primitive groups
were 651–660 bytes at 64 B and 651–658 bytes at 1,024 B.
These observed ranges are smaller than the binding's maximum and are
not bounds on future outputs.

| Unsigned input | Signed file (bytes) | Increase (bytes) | Ed25519 detached (bytes) | Falcon detached range (bytes) |
| --- | ---: | ---: | ---: | ---: |
| 742 B | 5,368 | 4,626 | 64 | 650–661 |
| 1 MiB | 1,053,202 | 4,626 | 64 | 650–660 |
| 10 MiB | 10,490,386 | 4,626 | 64 | 650–662 |

This table uses the unprofiled PDF observations. The fixed **4,626-byte**
total growth follows the default custom container capacities and
framing. It combines encoding, reserved space and metadata. It is
distinct from the sum of native signature lengths, and no single-layer
PDF format was introduced. The outer-gap canonicalization question
remains open under Phase 5.1A.
[Size derivation](phase5-1-implementation-evidence.md#pdf-preparation-and-signed-revisions) ·
[Integrity boundary](phase5-1a-signature-integrity-audit.md#impact-assessment)

## Artifacts and verification

The generated files are under
`%LOCALAPPDATA%\Temp\hybridsign-phase5-2a-_onmrwwz`. The directory
retains the three reproducible public inputs, the raw CSV, experiment
metadata, summary JSON and the two PNG charts. The signed output was
verified and measured on every trial and removed as an owned temporary
result. No key bytes, vaults, passwords or signature blobs are in the
data export.

| Artifact | SHA-256 |
| --- | --- |
| `raw.csv` | `7cbdde5a636f57554c555a4c867cb9da0dd55e9f374b2ecd7dfa859242e73b48` |
| `experiment.json` | `0243e205c5136d99c7a0a5d441f2d3851d4855e6a002fa4b675b3f1f847905c6` |
| `summary.json` | `56b6f6db7a01f458056b7f2007b7a0609a3f51c92ab5d3e1bbcfea2e43b93347` |
| `hybrid-pdf-median.png` | `09fa94e6a4ac6ad9f5b5b4680a92e6b9065af2d85a5b4c999227879444024b31` |
| `primitive-64b-median.png` | `cc55b602bf769ada0e4af0c8001104f1420d365087345355f1f8542c2a395e41` |

The first chart compares 64-byte primitive sign and verify medians in
microseconds. The second charts unprofiled sign/publish and external
verify medians across PDF sizes in milliseconds. Both start at zero.
Summary rows were recomputed from the raw CSV and matched exactly. The
fixture hashes were independently rechecked.

The focused run passed **204 tests in 5.88 s**, with zero failures, skips,
xfails or xpasses. It comprised 21 new harness tests and the 183 existing
tests selected in Phase 5.1A. The harness tests cover deterministic inputs,
xref/stream validation, scheduling, schema and units, native correctness,
staging/clock boundaries, verification failures, ownership and cleanup,
sanitized exception records and stopping on the admission budget. The
full GUI suite was outside this research-only run.
[Harness tests](../tests/test_research_benchmark_pilot.py) ·
[Existing test selectors](phase5-1a-signature-integrity-audit.md#raw-test-counts)

All 15 historical hashes, the public sample, the portable EXE and the
installer were checked against their existing records. The inherited CSVs
contain historical stage timings from different inputs and an undocumented
runtime environment. They remain a separate population. Even with matching
1 and 10 MiB sizes, this pilot cannot estimate a speedup from that older
system. The historical `50mb` fixture exceeds the current desktop's 50 MiB
signing limit. [Historical evidence and limitations](phase5-1-experiment-gap-analysis.md)

## Recommended Phase 5.2B plan

1. Freeze the harness revision and record the input hashes and run
   manifest schema before data collection. Repeat each selected condition
   in at least three fresh process sessions with declared warm-up and
   repetition counts. Record storage, power settings, foreground load
   and cache policy. Keep any cold-start series separate.
2. Retain paired primitive inputs and rotate or balance condition order
   within each session. Choose batching with a separately labelled pilot
   if very small calls need better clock precision. Report per-session
   variability and effect estimates with uncertainty that accounts for
   the session/block structure. Preserve slow samples and all failed
   trials.
3. Start with the validated PDF sizes. Extend to a 40 MiB fixture only
   when preflight and a labelled trial show adequate headroom. Separate
   published-file, candidate and UI/vault measurements. If peak memory is
   needed, use platform process accounting with fresh-process baseline
   and report exactly which resident or private-memory metric was
   observed. Do not infer native memory from Python-only tracing.
4. Keep canonicalization follow-up separate from timing claims. Maintain
   both accepted fixtures and covered-change/wrong-key checks. Keep the
   primitive comparisons and the existing hybrid pipeline as the thesis
   comparisons unless a distinct single-layer workflow is separately
   justified. Do not introduce new signed formats solely for timing.

## Changed files

- [Pilot harness](../research/benchmarks/phase5_2a.py)
- [Chart generator](../research/benchmarks/phase5_2a_charts.ps1)
- [Targeted research tests](../tests/test_research_benchmark_pilot.py)
- [Measurement methodology](phase5-2a-benchmark-methodology.md)
- This pilot analysis
