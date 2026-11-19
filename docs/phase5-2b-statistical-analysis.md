# Phase 5.2B — Statistical analysis and thesis interpretation

The three matched processes produced 90 observations per workload, operation and pipeline mode. Falcon-512 had higher median native signing latency and lower median native verification latency than Ed25519 for both matched message sizes in these runs. Median unprofiled PDF signing and independent verification times increased with each matched PDF size. The optional 40 MiB session extends the observed size range on the same host and is reported separately. [Experimental protocol and artifact inventory](phase5-2b-experimental-results.md)

## Analysis method

A trial is one scheduled primitive or pipeline visit. A metric is one observation within a trial. A signing trial may measure several stages, which share the trial and its process conditions. The analysis checks trial identity, order, status, metric completeness and units before calculating any statistic. It found no missing, failed or excluded trials. Only rows marked `measured` were used. All slow observations were retained.

The median is the middle observation or the average of the middle pair in sorted order. The mean is arithmetic. Sample standard deviation (SD) uses denominator `n − 1`. P95 uses linear interpolation at one-based rank `1 + 0.95 × (n − 1)` in sorted observations (Type 7). Sample SD requires at least two observations. P95 is reported for series of at least 30 observations to avoid a tail estimate from the single measured feasibility observation per condition. Timing uses the original integer elapsed nanoseconds. Tables convert to microseconds (µs) or milliseconds (ms) and round only for display.

The pooled distribution combines 30 measured observations from each of the three matched processes. Pooled SD describes observation-level dispersion across those three runs. A range of session medians shows between-session variation. With three runs on one host, the observed range is descriptive. There are no confidence intervals or p-values. The pooled P95 summarizes the recorded sample tail and does not establish a service-level guarantee.

The complete 871-row per-session CSV reports count, median, mean, sample SD, minimum, maximum and P95 for each operation, workload, mode and session. It includes separately labelled optional measurements, sizes and legacy timing slots. The 197-row aggregate CSV reports the same statistics for matched conditions plus the three session summaries. The ratios CSV retains all four comparisons for each process and for the matched aggregate. [Per-session statistics](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/per-session.csv>) · [Matched aggregate](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/matched-aggregate.csv>) · [Median ratios](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/matched-ratios.csv>) · [Analysis implementation](../research/benchmarks/phase5_2b_analysis.py)

## Primitive Ed25519 and Falcon-512

**Table 1. Matched pooled primitive latency (µs).**

| Workload | Algorithm | Operation | n | Median | Mean | Sample SD | Min | Max | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 64 B | Ed25519 | Keygen | 90 | 46.400 | 50.080 | 14.502 | 39.200 | 135.800 | 77.110 |
| 64 B | Falcon-512 | Keygen | 90 | 13,195.300 | 14,987.839 | 4,966.900 | 9,911.800 | 30,940.500 | 26,379.815 |
| 64 B | Ed25519 | Sign | 90 | 37.600 | 39.899 | 7.669 | 35.300 | 81.600 | 50.585 |
| 64 B | Falcon-512 | Sign | 90 | 4,357.250 | 4,409.324 | 274.568 | 4,193.600 | 6,346.400 | 4,830.035 |
| 64 B | Ed25519 | Verify | 90 | 90.650 | 94.426 | 12.465 | 86.000 | 187.700 | 110.685 |
| 64 B | Falcon-512 | Verify | 90 | 44.100 | 46.930 | 9.799 | 42.800 | 121.100 | 58.695 |
| 1,024 B | Ed25519 | Keygen | 90 | 39.500 | 42.207 | 9.300 | 35.300 | 95.800 | 53.120 |
| 1,024 B | Falcon-512 | Keygen | 90 | 12,726.800 | 14,280.580 | 5,053.701 | 9,831.000 | 39,999.100 | 23,814.435 |
| 1,024 B | Ed25519 | Sign | 90 | 39.950 | 41.727 | 9.098 | 37.500 | 121.200 | 45.440 |
| 1,024 B | Falcon-512 | Sign | 90 | 4,329.950 | 4,354.792 | 147.889 | 4,181.800 | 4,855.000 | 4,639.985 |
| 1,024 B | Ed25519 | Verify | 90 | 93.000 | 97.589 | 13.309 | 88.800 | 158.900 | 121.425 |
| 1,024 B | Falcon-512 | Verify | 90 | 48.250 | 50.327 | 8.453 | 46.400 | 103.000 | 53.405 |

**Table 2. Primitive latency medians by session (µs, 30 observations per cell).**

| Workload | Algorithm | Operation | matched-01 | matched-02 | matched-03 | Median of session medians | Between-session range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 64 B | Ed25519 | Keygen | 46.450 | 45.600 | 48.800 | 46.450 | 45.600–48.800 |
| 64 B | Falcon-512 | Keygen | 13,771.450 | 12,016.700 | 13,674.750 | 13,674.750 | 12,016.700–13,771.450 |
| 64 B | Ed25519 | Sign | 37.500 | 37.050 | 38.900 | 37.500 | 37.050–38.900 |
| 64 B | Falcon-512 | Sign | 4,265.550 | 4,328.400 | 4,417.950 | 4,328.400 | 4,265.550–4,417.950 |
| 64 B | Ed25519 | Verify | 90.300 | 90.500 | 93.450 | 90.500 | 90.300–93.450 |
| 64 B | Falcon-512 | Verify | 43.800 | 44.100 | 46.000 | 44.100 | 43.800–46.000 |
| 1,024 B | Ed25519 | Keygen | 38.300 | 39.600 | 40.700 | 39.600 | 38.300–40.700 |
| 1,024 B | Falcon-512 | Keygen | 12,377.250 | 14,480.400 | 11,645.000 | 12,377.250 | 11,645.000–14,480.400 |
| 1,024 B | Ed25519 | Sign | 39.100 | 39.950 | 40.750 | 39.950 | 39.100–40.750 |
| 1,024 B | Falcon-512 | Sign | 4,251.300 | 4,301.950 | 4,402.250 | 4,301.950 | 4,251.300–4,402.250 |
| 1,024 B | Ed25519 | Verify | 92.150 | 93.000 | 95.450 | 93.000 | 92.150–95.450 |
| 1,024 B | Falcon-512 | Verify | 47.700 | 48.100 | 49.750 | 48.100 | 47.700–49.750 |

**Table 3. Falcon-512 median latency divided by Ed25519 median latency.**

| Message | Operation | matched-01 | matched-02 | matched-03 | Pooled medians |
| --- | ---: | ---: | ---: | ---: | ---: |
| 64 B | Sign | 113.748× | 116.826× | 113.572× | 115.884× |
| 64 B | Verify | 0.485× | 0.487× | 0.492× | 0.486× |
| 1,024 B | Sign | 108.729× | 107.683× | 108.031× | 108.384× |
| 1,024 B | Verify | 0.518× | 0.517× | 0.521× | 0.519× |

The ratios compare equivalent public messages and positive timing scopes. The pooled native signing ratios are 115.88× at 64 bytes and 108.38× at 1,024 bytes. Native Falcon verification took about 49% and 52% of the corresponding Ed25519 medians. The direction of both differences held in each matched process.

A plausible contributor to Falcon's signing cost is lattice sampling in the PQClean implementation. Its verification follows a different computation. Ed25519 as called through PyNaCl uses libsodium's EdDSA implementation. The observed latencies include Python binding overhead and were measured at whole-call boundaries. This experiment does not attribute time to particular native instructions, sampling work or implementation optimizations. These ratios are specific to the tested implementations, calls, messages and host. [Phase 5.1 algorithm and implementation provenance](phase5-1-research-audit.md)

**Figures 1 and 2.** Individual session medians in µs. Figure 1 uses a logarithmic latency axis. Figure 2 uses a linear latency axis. [Primitive signing chart](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/primitive-sign.png>) · [Primitive verification chart](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/primitive-verify.png>)

## Hybrid PDF signing and independent verification

**Table 4. Matched pooled latency (ms) for the unprofiled PDF workflow.**

| Workload | Operation | n | Median | Mean | Sample SD | Min | Max | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 742 B | Sign and publish | 90 | 24.542 | 30.191 | 18.420 | 22.339 | 129.128 | 74.695 |
| 742 B | Verify published file | 90 | 0.382 | 0.400 | 0.063 | 0.336 | 0.706 | 0.511 |
| 1 MiB | Sign and publish | 90 | 48.253 | 52.777 | 16.134 | 45.692 | 137.663 | 64.912 |
| 1 MiB | Verify published file | 90 | 7.677 | 7.794 | 0.405 | 7.363 | 9.810 | 8.476 |
| 10 MiB | Sign and publish | 90 | 257.992 | 268.823 | 41.327 | 244.623 | 473.365 | 338.591 |
| 10 MiB | Verify published file | 90 | 73.749 | 74.348 | 2.281 | 71.257 | 81.349 | 78.110 |

**Table 5. Hybrid latency medians by session (ms, 30 observations per cell).**

| Workload | Operation | matched-01 | matched-02 | matched-03 | Median of session medians | Between-session range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 742 B | Sign and publish | 24.395 | 24.542 | 24.747 | 24.542 | 24.395–24.747 |
| 742 B | Verify published file | 0.415 | 0.380 | 0.369 | 0.380 | 0.369–0.415 |
| 1 MiB | Sign and publish | 48.823 | 47.701 | 48.761 | 48.761 | 47.701–48.823 |
| 1 MiB | Verify published file | 7.641 | 7.677 | 7.748 | 7.677 | 7.641–7.748 |
| 10 MiB | Sign and publish | 254.529 | 255.196 | 262.827 | 255.196 | 254.529–262.827 |
| 10 MiB | Verify published file | 72.400 | 73.374 | 75.429 | 73.374 | 72.400–75.429 |

**Figures 3 and 4.** Individual session medians in ms on linear latency axes. The first chart covers the call through atomic publication. The second covers a later read and verification of the published PDF. [Hybrid signing and publication chart](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/hybrid-sign.png>) · [Hybrid verification chart](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/hybrid-verify.png>)

**Table 6. Optional 40 MiB PDF, separate measured process (ms).**

| Workload | Operation | n | Median | Mean | Sample SD | Min | Max | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 40 MiB | Sign and publish | 30 | 1,081.842 | 1,154.928 | 295.140 | 992.816 | 2,599.060 | 1,489.751 |
| 40 MiB | Verify published file | 30 | 309.516 | 308.686 | 10.467 | 291.708 | 328.184 | 327.227 |

The 40 MiB supplement has one measured process with 30 observations per operation. The earlier feasibility case is reported in the archival CSV and excluded from Table 6. Comparing 1 MiB with 10 MiB in the matched pool, signing latency increased by 5.35× and verification by 9.61× at the median. Relative to the matched 10 MiB median, the separate 40 MiB median was 4.19× for signing and 4.20× for verification. That comparison also changes process, so it is exploratory. No timing is extrapolated to larger inputs.

The 742-byte sample and 1 MiB median signing times were closer together than their file sizes. Fixed overhead and changing per-byte work plausibly contribute. All observed positive timings passed the correctness checks. The spread between medians and high-tail observations, particularly for signing, is measured latency variation. The data do not identify the cause of individual slow trials.

## Profiled cost breakdown

**Table 7. Profiled elapsed median and sample SD in ms.** Columns give 90 observations per matched size and 30 for the optional size. Each size column reports median (SD).

| Stage | 742 B | 1 MiB | 10 MiB | 40 MiB, separate |
| --- | ---: | ---: | ---: | ---: |
| Capture source | 0.366 (0.071) | 0.580 (0.605) | 3.265 (0.354) | 12.732 (0.497) |
| Prepare Ed25519 container | 0.013 (0.010) | 0.559 (0.058) | 4.690 (0.202) | 19.254 (1.387) |
| Assemble Ed25519 covered ranges | 0.002 (0.005) | 0.422 (0.045) | 3.408 (0.300) | 14.355 (0.968) |
| Native Ed25519 signing | 0.053 (0.016) | 5.663 (0.276) | 57.604 (2.915) | 235.175 (12.058) |
| Embed Ed25519 signature | 0.035 (0.014) | 0.945 (0.088) | 8.446 (0.567) | 32.812 (1.760) |
| Prepare Falcon container | 0.016 (0.014) | 0.612 (0.291) | 5.051 (0.446) | 19.474 (1.447) |
| Apply SHAKE256 to Falcon covered ranges | 0.017 (0.010) | 2.617 (0.861) | 25.762 (1.203) | 109.700 (7.827) |
| Native Falcon signing | 4.418 (0.659) | 4.393 (0.807) | 4.392 (0.234) | 4.606 (0.243) |
| Embed Falcon signature | 0.086 (0.017) | 0.978 (0.118) | 8.591 (0.326) | 33.735 (1.553) |
| Write and fsync candidate | 1.918 (10.317) | 3.252 (17.713) | 14.189 (54.293) | 49.112 (7.802) |
| Verify staged candidate | 7.034 (1.914) | 14.791 (3.384) | 82.890 (5.197) | 320.643 (13.434) |
| Publish candidate | 0.386 (0.059) | 0.391 (0.036) | 0.389 (0.043) | 0.400 (0.039) |
| Total profiled signing call | 24.339 (14.422) | 48.933 (22.145) | 259.342 (61.990) | 1,083.612 (336.218) |

With default containers, Ed25519 received 845, 1,048,679, and 10,485,863 bytes at the three matched PDF sizes. The 40 MiB input gave it 41,943,143 bytes. The Ed25519 preparation helper joins the covered ranges. The Falcon prehash processes growing PDF revisions and its native signature call receives a fixed 64-byte SHAKE256 digest. For the matched sizes, the profiled median Ed25519 call, Falcon prehash, and staged self-verification rose with input length. The profiled median native Falcon call remained within 4.392–4.418 ms across those sizes. Repeated stages include reading and rewriting data, container parsing and embedding, fsync, strict pair checks, and public-key verification, with each timed at its stated boundary. The published-file verifier independently performs the positive hybrid checks later.

The profiled total is a separately observed wall time. Individual stage medians have no additivity guarantee and omit untimed work within the signing call. The candidate write and fsync stage includes disk I/O, and the publication stage includes the publisher's checks and replacement. Legacy timing slots remain separately labelled and are unsuitable as wall-clock totals. Peak resource use and storage-level persistence after power loss were not measured. [Pipeline timing boundaries](phase5-2b-experimental-results.md#measurement-boundaries)

## Interpretation and limits

- **Output growth.** All 734 new hybrid outputs were 4,626 bytes larger than their input. The default contents allocation consumes 4,352 of those bytes in encoded reserved space. An additional 274 bytes are framing and metadata. Native Falcon signature lengths varied without changing output size. This result is specific to the HybridSign default containers. [Output size table and derivation](phase5-2b-experimental-results.md#correctness-and-output-sizes)
- **Measured scope.** These results support relative latency and size observations for the specified Python calls and audited host. Three processes expose run-to-run effects under similar conditions. Different machines, storage, background activity, process configuration, libraries, and GUI or vault work can change timings. The pilot and inherited measurements were preserved separately because historical scopes and conditions do not establish a matched comparison.
- **Validity and conformance.** Positive checks confirmed mathematical validity with the tested public keys, and the chosen covered edit and wrong keys were rejected. Signer identity and timestamp trust are separate questions. The Phase 5.1A native Falcon encoding question remains open, including whether more than one accepted representation can occupy the outer signature storage gap. These trials do not establish exhaustive final-file canonicalization or Falcon specification conformance. The package and native revision identify the tested implementation. [Phase 5.1A integrity audit](phase5-1a-signature-integrity-audit.md) · [Falcon conformance assessment](phase5-1-research-audit.md)

## Recommended thesis wording

> On one Windows 11 Pro computer, we ran three separate Python processes with 30 measured trials per condition in each process. For identical 64-byte and 1,024-byte inputs, the measured Falcon-512 signing medians were approximately 116× and 108× the Ed25519 medians. Falcon-512 verification medians were approximately 49% and 52% of the corresponding Ed25519 medians. With HybridSign's default containers, verified hybrid PDFs were 4,626 bytes larger than their unsigned inputs. Median local signing and publication took 24.54, 48.25 and 257.99 ms for the 742-byte sample, 1 MiB and 10 MiB, respectively. Median independent verification took 0.382, 7.677 and 73.749 ms for the same inputs. Every tested positive output verified with the corresponding public keys. The selected covered content mutation and wrong keys were rejected in the hybrid controls. The experiment characterizes this implementation under the recorded conditions. Signer identity and canonicalization of every final byte were outside the evidence established by these measurements.
