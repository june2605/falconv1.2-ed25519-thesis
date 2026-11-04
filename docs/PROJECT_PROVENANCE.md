# Project Provenance

## Original Research

This undergraduate thesis project builds upon the Falcon-Ed25519 hybrid digital signature research prototype.

Original repository: https://github.com/luluon-cyper/FALCON

Inherited baseline commit: 0f3b513

## Development History

- 990b946: Phase 1 - Baseline regression tests and verification UI fix
- f421879: Phase 2B.1 - Signature container and ByteRange validation
- 39821b0: Phase 2B.2 - Canonical signature metadata and padding validation

## Repository Migration

This lightweight thesis repository was created from the source tree at commit 39821b0.

Large benchmark datasets and Git LFS objects were intentionally excluded.

The original local repository at D:\Final_Thesis retains the complete inherited history and benchmark data.

## Validation Baseline

- Python: 3.11.9
- Signature scheme: Ed25519 followed by Falcon-512
- Regression tests: 294 passed
- Expected failures: 0

These results do not establish complete system security or PDF signature standards compliance.
