# Phase 5.2B — Multi-session experimental results

Five fresh Python processes on one Windows host completed on 19 November 2026. Three matched sessions established the primary result. A feasibility process and a separate measured process evaluated the optional 40 MiB PDF. Every newly signed output passed its corresponding positive verification check. The matched sessions produced 90 measured observations per condition. The companion report presents timing tables, session comparisons, and limits on the conclusions. [Statistical analysis](phase5-2b-statistical-analysis.md)

## Source and preserved pilot

The starting worktree at `D:\Final_Thesis_GitHub` was clean on `thesis/ui-demo` at `3ebfe31abb080a0355ac512d6190910d33e98a63`. The measurement metadata reports a dirty worktree because the new research and test files were present during collection. Source hashes for the six measured production modules matched the committed bytes. All processes used the unchanged `phase5_2a.py` v1.0.0 harness, SHA-256 `29a697ca3d4063773e3be9856a9a3e70fba7d4671e37c89613d0fc775a579410`. [Measurement harness](../research/benchmarks/phase5_2a.py)

All eight original pilot artifacts were present in `%LOCALAPPDATA%\Temp\hybridsign-phase5-2a-_onmrwwz`. Their bytes matched the original recorded hashes before and after this experiment. The collector made exclusive copies in the durable campaign folder outside Git and Windows Temp. None of these observations enter the new statistics. [Phase 5.2A report](phase5-2a-pilot-analysis.md) · [Pilot copy manifest](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/phase5-2a-preserved/archive-checksums.json>)

| Archived pilot file | SHA-256 |
| --- | --- |
| `1-MiB.pdf` | `568830f43d6be53c262a29d679ab97bb02afcd44418a839a10d26ece85ca6490` |
| `10-MiB.pdf` | `34061f01468d32fa023756bfc0b225d703d31c2275a387cf68cc2139ad4cdec5` |
| `demo.pdf` | `2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639` |
| `experiment.json` | `0243e205c5136d99c7a0a5d441f2d3851d4855e6a002fa4b675b3f1f847905c6` |
| `hybrid-pdf-median.png` | `09fa94e6a4ac6ad9f5b5b4680a92e6b9065af2d85a5b4c999227879444024b31` |
| `primitive-64b-median.png` | `cc55b602bf769ada0e4af0c8001104f1420d365087345355f1f8542c2a395e41` |
| `raw.csv` | `7cbdde5a636f57554c555a4c867cb9da0dd55e9f374b2ecd7dfa859242e73b48` |
| `summary.json` | `56b6f6db7a01f458056b7f2007b7a0609a3f51c92ab5d3e1bbcfea2e43b93347` |

## Conditions and per-process counts

| Session | Python PID | Experiment ID | Start–end (ICT) | Process wall (s) | Warm-up / measured blocks | Warm-up / measured trials | Raw rows |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| `matched-01` | 23808 | `947a29d1-20d5-4bec-ac88-c4b6246078bc` | 17:25:02.818–17:25:47.316 | 44.497 | 3 / 30 | 36 / 360 | 6,501 |
| `matched-02` | 11940 | `557b4525-a5c4-45bd-bc65-13702c0cc449` | 17:25:52.129–17:26:35.526 | 43.396 | 3 / 30 | 36 / 360 | 6,501 |
| `matched-03` | 24448 | `891a1e44-20d4-496e-bb42-c5bf4d804457` | 17:26:40.431–17:27:25.460 | 45.029 | 3 / 30 | 36 / 360 | 6,501 |
| `optional-40-feasibility` | 18908 | `a582ff1a-6aea-438d-930c-7f7ff110e8f4` | 17:27:32.871–17:27:43.843 | 10.973 | 1 / 1 | 10 / 10 | 280 |
| `optional-40-measured` | 24084 | `15131c1f-2d5d-4b31-abde-8b23576e3e38` | 17:29:26.974–17:31:56.063 | 149.089 | 3 / 30 | 30 / 300 | 4,620 |

These are Python interpreter PIDs. `session.json` also records the Windows launcher PID. UTC timestamps with full precision are in the records. Each matched block ran 12 trials. It included two public-message preparations, four primitive trials, and six hybrid trials. Each primitive trial measured key generation, signing, and verification of the same public bytes. Each PDF ran once in each pipeline mode. The optional blocks used the unchanged schedule with the public sample and 40 MiB, yielding ten trials per block. Controls and comparisons reused the exact public input for each corresponding workload. [Collector](../research/benchmarks/phase5_2b_collect.py) · [Schedule](../research/benchmarks/phase5_2a.py#L348)

| Workload | Size (bytes) | SHA-256 of exact input |
| --- | ---: | --- |
| `64-byte shared message` | 64 | `c3dd5c7931dc193d1fd298d1b3bf60836161f6d36bca5424fcfbb9a0282cc1d0` |
| `1024-byte shared message` | 1,024 | `7f26905582c804ce21a9aae762c8c83f82290c6a1bed9556da63fe0c6b98cb29` |
| `demo.pdf` | 742 | `2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639` |
| `1-MiB.pdf` | 1,048,576 | `568830f43d6be53c262a29d679ab97bb02afcd44418a839a10d26ece85ca6490` |
| `10-MiB.pdf` | 10,485,760 | `34061f01468d32fa023756bfc0b225d703d31c2275a387cf68cc2139ad4cdec5` |
| `40-MiB.pdf` | 41,943,040 | `1ea76c9c66aa832b8a26aa649c5678f570b9069904d043947c161847d989c3be` |

The 742-byte tracked public sample is copied verbatim. The other PDFs are deterministic exact-size fixtures with a valid PDF trailer and cross-reference structure verified by the harness. Each is unsigned before timing and retains a unique covered text token for the negative control. Neither the 200 MB nor 500 MB workload ran. [Fixture generation and validation](../research/benchmarks/phase5_2a.py#L77)

- Intel Core i7-10850H at nominal 2.70 GHz, 6 physical cores and 12 logical processors, 16,762,388,480 bytes installed RAM reported by Windows. Windows 11 Pro AMD64 build `26200.9974`, local fixed NTFS output volume. All sessions recorded AC power, Balanced plan and battery saver off at entry and exit. Available RAM and free disk are recorded per process.
- CPython 3.11.9, PyNaCl 1.6.2, pqcrypto 0.3.4. The local environment also reported cryptography 50.0.2. The measured Falcon binding is `falcon_512`, PQClean clean, vendored revision `2cc64716044832eea747234ddbffc06746ab815d`, native module SHA-256 `ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237`.
- The benchmark ran sequentially with one active Python thread at process entry and exit. Default GC stayed enabled with thresholds `700, 10, 10` and a `0.005 s` Python switch interval. No GC disabling, CPU affinity, forced clock, native thread setting, or cache flush was used. No Playwright, native GUI automation, or second controlled benchmark job ran concurrently. Background OS load and CPU frequency were not controlled.
- The first three blocks warm up each matched workload in each new process. Warm-up rows stay in the raw data and are excluded from the statistics. Each block prepares the 64-byte message before the 1,024-byte message. Primitive algorithm order reverses on even blocks, PDF order rotates by block, and the order of profiled and unprofiled signing alternates. The schedule is deterministic and uses no seed. Cryptographic randomness uses the libraries' normal sources.

## Measurement boundaries

`perf_counter_ns()` uses the Windows elapsed performance counter with 100 ns reported resolution. A primitive signing timer encloses the native signing call with an already generated key and public message. Ed25519 extracts the detached signature from the returned object outside that timer. Primitive verification clocks one positive detached check given the matched public key, message, and signature. Public-message preparation, key generation and negative checks have separate scopes.

`sign_and_publish` measures the uninstrumented call to `sign_with_key_material()` from entry through return, including source capture, key checks, staging, candidate verification and atomic publication. The candidate is flushed, fsynced and closed before verification. `verify_published_file` independently measures a later `verify_file_with_public_keys()` call on the already published file, with file I/O and both signature layers. Temporary fixture generation, vault unlock, GUI rendering, and native dialogs are outside both timings. The profiled run wraps actual operations inside the same signer. It reports separate Ed25519 message assembly, the native Ed25519 call, each container preparation and embedding, Falcon SHAKE256 prehash, the native Falcon call, candidate writing and fsync, candidate self-verification, and publication. Legacy timing slots are archived separately as seconds. [Profile and trial definitions](../research/benchmarks/phase5_2a.py#L184) · [Production signing entry point](../sign.py#L43)

The Ed25519 helper named `compute_sha512_digest_for_byte_range()` concatenates the covered byte ranges. Ed25519 receives the resulting bytes directly. Falcon receives a 64-byte SHAKE256 digest of its covered ranges, including the complete Ed25519 container. The raw CSV has separate fields for elapsed nanoseconds, legacy timing seconds, and measured sizes in bytes. It keys observations by experiment, mode, workload, algorithm, phase, repetition, scheduled order and operation. [ByteRange helpers](../utils.py#L267) · [Phase 5.1A integrity audit](phase5-1a-signature-integrity-audit.md)

## Optional 40 MiB decision

The preflight validated the exact 41,943,040-byte fixture and PDF structure and confirmed it is below the unchanged desktop limit of 52,428,800 bytes. The signing transaction can hold the captured source and successive prepared and signed revisions, along with concatenated covered bytes and verification buffers. On disk it holds the source snapshot, Ed25519 prepared and signed stages, the Falcon prepared stage, and a final candidate. The reserve allowed 48 input-size copies in RAM as a conservative admission bound and ten input-size intermediate disk copies plus the public fixture and 64 MiB in disk headroom. These are planning estimates. Peak working set and actual disk high-water mark were not measured.

| Preflight resource | Required reserve (bytes) | Available first check (bytes) | Available before supplement (bytes) |
| --- | ---: | ---: | ---: |
| RAM | 2,013,265,920 | 7,229,509,632 | 7,250,800,640 |
| Disk | 528,482,304 | 18,608,349,184 | 18,564,227,072 |

The single warm-up and measured 40 MiB feasibility blocks passed all checks. The 10.973 s full-process wall time, multiplied by 33 blocks, gave a conservative admission estimate of 362.111 s. That exceeded the initial 300 s gate. The original decision is preserved in `collection.json` and `optional-40-preflight.json`. After a resource recheck, the separate append-only supplement used the harness's supported 600 s admission budget. It completed in 149.089 s with three warm-up and 30 measured trials per mode for 40 MiB. The ceiling governs admission of further trials and does not terminate an in-progress operation. Feasibility and supplement data stay separate from the three matched sessions. [Harness budget](../research/benchmarks/phase5_2a.py#L381) · [Initial optional preflight](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-40-preflight.json>) · [Supplement record](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-extension.json>)

## Correctness and output sizes

All five sessions completed with zero failed or excluded trial rows. The logs contain 24,403 raw metric rows across 1,538 trials. Of those trials, 1,390 were measured and 148 were warm-up. Across both phases, 536 primitive signatures verified with their matching public keys and rejected the modified message. All 734 hybrid outputs verified against both public keys, preserved the input prefix and parsed as a strict pair. Each rejected an equal-length modification of covered content and rejected a wrong public-key pair. These controls ran on each signed output, including both pipeline modes. Their negative checks are outside the reported positive operation elapsed times.

| PDF | Input bytes | Published bytes | Increase (bytes) | Outputs checked | Falcon signature min–max (native bytes) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 742 B | 742 | 5,368 | 4,626 | 268 | 649–660 |
| 1 MiB | 1,048,576 | 1,053,202 | 4,626 | 198 | 651–662 |
| 10 MiB | 10,485,760 | 10,490,386 | 4,626 | 198 | 650–661 |
| 40 MiB (supplement and feasibility) | 41,943,040 | 41,947,666 | 4,626 | 70 | 650–661 |

Ed25519 signatures were 64 native bytes throughout. Default capacities reserve 128 and 2,048 signature bytes, represented by 256 and 4,096 on-disk hexadecimal characters. Framing and metadata contribute 274 further bytes in total. The 4,626-byte increase is the difference between published PDF length and input length on every checked hybrid output. It measures storage overhead of this exact default format. It includes reserved padding and is independent of the observed variation in native Falcon length. [Default capacity and trailer construction](../utils.py#L223)

The current PDF format checks validity with supplied public keys. It does not supply trusted signer identity or a trusted timestamp. Native Falcon encoding canonicalization and exhaustive detection of changes in the excluded outer storage gap remain open. The covered-edit control provides specific verification evidence. [Phase 5.1A findings](phase5-1a-signature-integrity-audit.md)

## Durable data and charts

Each link below points to the actual local artifact. `experiment.json` and `summary.json` are alongside `raw.csv`. The parent session directory holds `session.json` and the process log. The [campaign inventory](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/checksums.sha256>) contains 59 SHA-256 entries covering the archives, raw rows, final plots, fixtures, and execution metadata. Its own SHA-256 is `f96d025145a113009eb3224fa9129b1985dd1fb3b13cee983a49a424e1679da3`. The campaign is preserved at `C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5`.

| Session raw CSV | Raw CSV SHA-256 | Experiment JSON SHA-256 |
| --- | --- | --- |
| [matched-01](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/matched-01/hybridsign-phase5-2a-ujk7cemj/raw.csv>) | `2f593201c15bbec63dfa36645fdfd77af284e21614d0fe7230d4ceb98f406c15` | `81a7d5b4330808598fba2538988a0108e5a695075aa050270b674a19d77db807` |
| [matched-02](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/matched-02/hybridsign-phase5-2a-9eglstai/raw.csv>) | `a453929eb65a6bbc3651c413ca6c05de5d375b6c8cfbf6df1e79282677a35d8a` | `4eb02c9ec6d4123ef879f042375d0b70dd2022b50bec6b589843fa2e05ec3a70` |
| [matched-03](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/matched-03/hybridsign-phase5-2a-hr6dfrst/raw.csv>) | `5a660fed8ca726a54ab99d453d25d3e24cf241e84869f0666850595da52d8418` | `deb0c3e5dafb99f146455580380d493ef73299e7524a7867ad771e2878f47a35` |
| [optional-40-feasibility](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-40-feasibility/hybridsign-phase5-2a-mg3q8ba9/raw.csv>) | `a5d8ba79de58f270d21d70edda74cca519854195ec1ad424aba87e714388cad9` | `8b66c54d19c7b96da053937924fc59cd98af4c883768549a9bceb5e3014a7a3f` |
| [optional-40-measured](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-40-measured/hybridsign-phase5-2a-uyfh4kd9/raw.csv>) | `2baf2cb948f11ef1cdeec9ed1d1077865f0fa21cae699a1aaf04be596b3df3dc` | `03718a7db123bc179d2ae384f21403cfce66072a14dde75bf3833344b293bec2` |

| Figure (1,400 × 820 PNG) | SHA-256 |
| --- | --- |
| [hybrid-sign.png](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/hybrid-sign.png>) | `96e2cdca213f26310400f07ab10fe3de3abfa89f9eebd7e31fee974de2a6da02` |
| [hybrid-verify.png](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/hybrid-verify.png>) | `4c048da990f9c45aa7cd98d67ba01ce95ab06f5b3d12ba17333f33dd9283e2d0` |
| [primitive-sign.png](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/primitive-sign.png>) | `5ef65a1a9b7f915bb11c18da4a89707a70c66cef214d5c0ee86b5d64b05de8eb` |
| [primitive-verify.png](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/primitive-verify.png>) | `cb70a38e28d276286902fa8ef0f6b224983a70fe5e5702489c70f907a3b8a56d` |

The signing figure for primitive operations uses a logarithmic latency scale. The other charts use linear latency axes. Marked points show individual session medians. Each matched condition includes three points of 30 measured observations apiece. The optional 40 MiB workload appears in the separate results table, with no cross-session figure. The size table shows the invariant overhead directly.

## Reproduction

Use Windows PowerShell from the repository root and the existing Python 3.11.9 virtual environment. Keep the reviewed Phase 5.2B research files with the committed baseline. Use an existing output root on a local fixed volume outside Git. Assign `$campaign` and `$analysis` from the paths printed by the commands. The archived pilot copies can seed a new campaign. Each run and each analysis uses a fresh directory.

```powershell
$reference = Join-Path $env:LOCALAPPDATA 'HybridSignResearch\phase5-2b\campaign-l54v36l5'
$root = Split-Path -Parent $reference
$pilot = Join-Path $reference 'phase5-2a-preserved'
.\.venv\Scripts\python.exe -B -m research.benchmarks.phase5_2b_collect --output-root $root --pilot-source $pilot --include-40
```

If the collector records `not_run_after_feasibility`, assign `$campaign` to the newly printed path and use the archived supplementary command only after confirming the current resource and time gates. The command rechecks them and records the continuation separately. If the collector already completed the optional measurement, proceed to analysis.

```powershell
Get-Content -Raw -LiteralPath (Join-Path $reference 'optional-supplement-command.py') | .\.venv\Scripts\python.exe -B - $campaign
```

To regenerate the charts and tables for the original observations, assign `$campaign = $reference`. For fresh results use the new campaign path. Run the analysis, assign the printed analysis directory to `$analysis`, then generate the charts and inventory.

```powershell
.\.venv\Scripts\python.exe -B -m research.benchmarks.phase5_2b_analysis --campaign $campaign
.\research\benchmarks\phase5_2b_charts.ps1 -AnalysisDirectory $analysis
.\.venv\Scripts\python.exe -B -m research.benchmarks.phase5_2b_analysis --campaign $campaign --inventory $analysis
```

A second analysis of the preserved raw data reproduced all four charts and four analysis files byte for byte on this host. Alternate machines, fonts, or .NET versions can change PNG rendering. A fresh benchmark produces new statistical observations.

## Regression and release integrity

Two focused runs each completed with **220 passed**, in 6.43 s and 5.87 s. Each comprised 183 Phase 5.1A focused signing, parser, and verification cases, 21 Phase 5.2A harness cases and 16 new session-analysis and preservation cases. Both had zero failures, skips, xfails or xpasses. The command used `.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` with the Phase 5.1A focused selectors and the two benchmark test files. The complete application and native GUI suites were outside this phase's focused run. [Existing focused selectors](phase5-1a-signature-integrity-audit.md#raw-test-counts) · [Pilot harness tests](../tests/test_research_benchmark_pilot.py) · [Session tests](../tests/test_research_benchmark_sessions.py)

All 15 historical benchmark hashes, the public sample hash, the eight original pilot/copy pairs, and all 59 campaign inventory entries matched. The installed release was not exercised. The existing approved 138-file portable payload, portable ZIP and per-user installer matched their recorded hashes. The changes are confined to research collection, analysis, tests, and documentation, so the release binaries require no rebuild. The evidence folder contains public inputs, aggregate and raw measurements, and provenance records. Temporary signing artifacts, private keys, passwords and large generated PDFs were kept outside Git. [Release inventory methodology](phase4c2b-installer-release.md)

| Changed file | Scope |
| --- | --- |
| [research/benchmarks/phase5_2b_collect.py](../research/benchmarks/phase5_2b_collect.py) | Archive pilot evidence, record host and process provenance, and schedule sequential runs |
| [research/benchmarks/phase5_2b_analysis.py](../research/benchmarks/phase5_2b_analysis.py) | Validate trial completeness and compute descriptives, ratios and artifact checksums |
| [research/benchmarks/phase5_2b_charts.ps1](../research/benchmarks/phase5_2b_charts.ps1) | Render four reproducible charts with Windows PowerShell and .NET charting |
| [tests/test_research_benchmark_sessions.py](../tests/test_research_benchmark_sessions.py) | Test preservation, schedule validation, statistics and optional-run bookkeeping |
| [docs/phase5-2b-experimental-results.md](phase5-2b-experimental-results.md) | Record experiment, data, integrity, and reproduction |
| [docs/phase5-2b-statistical-analysis.md](phase5-2b-statistical-analysis.md) | Present timing statistics, session variation, and thesis interpretation |
