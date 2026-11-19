# Phase 5.1 — Thesis claim traceability and chapter structure

The statuses below apply to each claim as worded. **Directly supported**
means primary material and available implementation or data evidence
establish the scoped statement. **Partially supported** means available
evidence covers a narrower statement. **Not yet supported** identifies
work that remains. **Requires correction** identifies a statement that
conflicts with the source or exceeds its evidence.

A = inherited measurements. B = current implementation or functional
regression evidence. C = independent Phase 5.2 experiments,
which are proposed. [Research audit](phase5-1-research-audit.md) ·
[Implementation and diagram](phase5-1-implementation-evidence.md) ·
[Research experiment protocol](phase5-1-experiment-gap-analysis.md)

## Research questions

| Question | Current answer | Evidence decision |
| --- | --- | --- |
| RQ1 — How is the nested construction implemented? | With exact bounded ByteRanges, pure Ed25519 over the first-revision slices, then Falcon-512 over a 64-byte SHAKE256 digest that binds the complete Ed25519 container. Each layer omits its own gap. The current verifier requires one adjacent complete pair. | **Directly supported.** Source reconstruction and existing independent message tests. No new performance experiment is needed to describe the construction. |
| RQ2 — Does verification reject modified PDFs and wrong keys? | Yes for the independently exercised content, wrong/mixed keys, trailer, range and layer-failure cases. The same claim about every possible change in final bytes exceeds the evidence. | **Directly supported under tested conditions.** The outer native encoding-equivalence question requires a separate follow-up. |
| RQ3 — What are the performance and storage costs versus the individual algorithms? | The old hybrid CSVs support scoped descriptive results. Default raw/serialized sizes are known from the binding and layout. There are no matched single-algorithm or current full-pipeline latency/memory experiments for this comparison. | **Partially supported.** Phase 5.2 needs measurements with comparable boundaries. |
| RQ4 — What limitations remain for use? | Provenance, cryptographic validity and local vault authentication have separate meanings. Threats include trust-source substitution, local compromise, offline password guesses and incomplete compatibility. There is no trusted identity/time or public compliance evidence. | **Directly supported as an audit of design boundaries.** Resistance to the broader threats is not established. |
| RQ5 — How should the Falcon version be described? | Cite Falcon specification v1.2 for theory and identify the actual `pqcrypto==0.3.4` PQClean clean `falcon_512` binding and pinned source lineage for experiments. | **Directly supported as identification.** Full conformance, independent reproducibility and FIPS validation remain unestablished. |

## Claim-to-evidence matrix

| Thesis claim and status | Theoretical or primary source | Exact implementation | Test / experiment evidence | Remaining limit or decision |
| --- | --- | --- | --- | --- |
| **Directly supported** — The inner layer uses pure Ed25519 with a 32-byte seed/public key and a 64-byte signature. | [RFC 8032 §5.1](https://www.rfc-editor.org/rfc/rfc8032.html#section-5.1) · [Libsodium](https://doc.libsodium.org/public-key_cryptography/public-key_signatures) | [`keygen.generate_hybrid_key_pair()`](../keygen.py#L6) · [`utils.compute_sha512_digest_for_byte_range()`](../utils.py#L267) · [`sign._sign_captured()`](../sign.py#L74) | **B** Exact message reconstruction and native verification in [`test_signatures_cover_the_inherited_sequential_messages`](../tests/test_hybrid.py#L57). Wheel wrapper/native bytes match. | A local standards-vector run is separate from application regressions. `ed_hash` is a legacy timing label for joining bytes. |
| **Directly supported** — Falcon is the 0.3.4 `falcon_512` PQClean clean binding of the documented lineage. | [PyPI artifact metadata](https://pypi.org/pypi/pqcrypto/0.3.4/json) · [Pinned PQClean metadata](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/META.yml) | [Native generation, validation and signing](../keygen.py) · [`hybrid_keys.validate_key_pair()`](../hybrid_keys.py#L100) · [Outer call](../sign.py#L124) | **B** Published wheel hashes and local module/native matches, inspected attestation fields, pinned gitlink and round trips. [Lineage](phase5-1-research-audit.md#falcon-implementation-and-version-boundaries) | Attestation chain/transparency unverified. No reproducible rebuild. |
| **Requires correction** — “The library is Falcon v1.2 certified/FIPS 206 compliant.” | [Falcon submission v1.2](https://falcon-sign.info/falcon.pdf) · [NIST standardization status](https://csrc.nist.gov/projects/post-quantum-cryptography/post-quantum-cryptography-standardization) | The code calls `falcon_512`, whose detached format is identified in the [pinned native wrapper](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/pqclean.c). | **B** Round trips and fixed PDFs establish tested compatibility. Upstream KAT hashes were inspected without rerunning the KAT. | State the spec separately. **C** A conformance scope would need vectors, source-to-spec mapping and independent evidence. |
| **Directly supported** — Falcon signs a later revision that incorporates the complete Ed25519 container. The current verifier requires both. | [RFC 9794 vocabulary](https://www.rfc-editor.org/rfc/rfc9794.html) · [RFC 9955](https://www.rfc-editor.org/rfc/rfc9955.html) · [FIPS 202 SHAKE definition](https://csrc.nist.gov/pubs/fips/202/final) | [`sign._sign_captured()`](../sign.py#L74) · [`utils.compute_shake256_digest_for_byte_range()`](../utils.py#L276) · [`utils.parse_signature_pair()`](../utils.py#L190) · [`verify._verify_document()`](../verify.py#L48) | **B** [Sequential messages](../tests/test_hybrid.py#L57), [pair order and suffix](../tests/test_signature_pair.py) and [either layer failed](../tests/test_hybrid.py#L103). | Boolean result applies to the complete pair. Cross-protocol stripping behavior requires separate analysis. |
| **Not yet supported** — A formal hybrid unforgeability, non-separability or quantum-resistance theorem for this construction. | [Bindel et al., hybrid unforgeability and non-separability](https://eprint.iacr.org/2017/460) · [RFC 9955](https://www.rfc-editor.org/rfc/rfc9955.html) | Concrete grammar, messages and checks in [`utils.py`](../utils.py), [`sign.py`](../sign.py) and [`verify.py`](../verify.py). | **B** Functional tests require both layers under the supplied keys. **C** Broader negative controls are planned. | Formal claim needs a defined adversary, security goal, hash and parsing assumptions, trusted key binding and a reduction. Test volume cannot prove it. |
| **Directly supported** — Tested covered edits, wrong/mixed keys, malformed structure, nonzero padding and appended bytes reject. | Digest and signature principles in [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032.html) and [Falcon v1.2](https://falcon-sign.info/falcon.pdf). The grammar is defined by this project. | [`utils._validate_byte_range()`](../utils.py#L102) · [`parse_completed_signature()`](../utils.py#L164) · [`VerificationService.run()`](../desktop/verification_service.py#L41) | **B** [Hybrid tests](../tests/test_hybrid.py#L81), [completion](../tests/test_completed_signatures.py), [whole pair](../tests/test_signature_pair.py), [desktop verifier](../tests/test_desktop_verification.py#L66) and recorded actual EXE behavior. | Each outcome refers to its tested mutation and selected byte revision. No identity assertion follows. |
| **Requires correction** — “Every final signed byte is cryptographically covered or has a unique accepted representation.” | [Pinned Falcon decoder compatibility logic](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/pqclean.c#L228-L247) | The final gap is outside the native message, and the PDF parser does syntax/size/padding checks. [`utils.parse_signature_container()`](../utils.py#L119) · [`parse_completed_signature()`](../utils.py#L164) | **B** Tests cover nonzero changes in unused ASCII padding and particular `SigLength` changes. No new end-to-end encoding-equivalence case was run. | **C** Review whether native padded compatibility gives alternate PDF representations and how a canonical encoding policy would affect existing signatures. [Analysis](phase5-1-implementation-evidence.md#security-interpretation-and-representation-limit) |
| **Directly supported** — Passphrase-derived authenticated encryption protects saved private key material and checks header/ciphertext on unlock. | [RFC 9106](https://www.rfc-editor.org/rfc/rfc9106.html) · [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final) · [FIPS 197](https://csrc.nist.gov/pubs/fips/197/final) | [`vault_crypto._derive_key()`, `_seal_key_pair()`, `unseal_key_pair()`](../vault_crypto.py) · [Format layout](phase3-2-vault-format.md) | **B** [Official primitive vectors and round trips](../tests/test_vault_crypto.py), [wrong password](../tests/test_vault_crypto.py#L91) and [AAD mutation](../tests/test_vault_crypto.py#L172). | Depends on password quality, entropy, implementation and OS. Offline guessing and vault replacement/rollback remain possible threats. |
| **Directly supported** — The controlled native signer uses original keys in its worker, supports lock/reopen and keeps plaintext keys off disk on that path. | [Vault threat assumptions](phase3-2b3-regression.md) | [`vault._managed_key_access()`](../vault.py#L150) · [`VaultService.lock_active()`](../desktop/vault_service.py#L88) · [`sign_vault_document()`](../vault_signing.py#L61) | **B** [No plaintext writes/logs](../tests/test_vault_signing.py#L343), [cross-process recovery](../tests/test_vault_signing.py#L438) and [installed/portable demo](phase4c3-final-release-review.md). | No guaranteed memory zeroization or protection from local malware. Legacy raw key-export paths have different behavior. |
| **Requires correction** — “Hybrid Key ID, vault unlock or HYBRID VALID proves who signed or when.” | [RFC 9955 on protocol and policy](https://www.rfc-editor.org/rfc/rfc9955.html) · [Project verification trust model](phase4b3b-real-verification-regression.md#public-key-source-trust) | [`hybrid_keys.hybrid_key_id()`](../hybrid_keys.py#L50) · [`VerificationService.select_keys()`](../desktop/verification_service.py#L24) | **B** [ID formula](../tests/test_key_material.py#L74), [matching results and source trust](../tests/test_desktop_verification.py#L66) and [password-free metadata behavior](../tests/test_desktop_verification.py#L225). | It identifies an ordered public-key tuple. Identity binding, authorization, revocation and trusted timestamps are absent. |
| **Directly supported** — Default file growth is 4,626 bytes, with 929 raw public-key bytes and a 2,416-byte local vault. | [Native signature bounds](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/api.h) · [Vault format](phase3-2-vault-format.md) | [`DEFAULT_SIGNATURE_CAPACITIES` and template](../utils.py#L9) · [`HybridPublicKey`](../hybrid_keys.py#L66) | **B** Direct byte accounting and observed demo growth 742 → 5,368. [Size derivation](phase5-1-implementation-evidence.md#pdf-preparation-and-signed-revisions) | Default profile only. Custom capacities change PDF growth and native Falcon lengths vary. |
| **Partially supported** — Larger files increased recorded hybrid timing and current relative costs can be estimated. | [Analysis and clock scope](phase5-1-experiment-gap-analysis.md) | Historical [driver](https://github.com/luluon-cyper/FALCON/blob/7f199dd3bc89b4dd2e2c5f3f71dc4751a3c87f01/demo.py) · Current [transaction](../signing_io.py#L114) | **A** 100 signing and verification observations per label. Those observations support an association in the inherited corpus only. | **C** Relative Ed-only/Falcon-only/current hybrid overhead needs contemporaneous controls. Hardware unknown. Stage fields and product latency differ. |
| **Not yet supported** — CMS, PAdES, Adobe signature-panel or production readiness. | [Project deployment and release scope](phase4c3-final-release-review.md#readiness-and-remaining-acceptance) | Custom markers and independent parser in [`utils.py`](../utils.py). | **B** Source, native and packaged tests on documented Windows profiles. | Cross-reader/standards verification, trusted key infrastructure and independent review are separate work. Clean-Windows-VM acceptance remains absent. |

## Proposed chapter structure

No university thesis template, rubric, approved outline or review notes were
found in either inspected project tree. The proposed chapters organize
technical evidence and should be aligned to the faculty's actual requirements
once supplied.

1. **Problem and research scope.** Frame migration to post-quantum
   signatures, state RQ1–RQ5, and identify FALCON/eSign and HybridSign as
   inherited research and its thesis extension.
2. **Cryptographic background.** Explain EdDSA/Ed25519, the Falcon v1.2
   design, selected Falcon-512 parameters, security notions and PQ/traditional
   hybrid terminology. Explicitly separate the specification and bound library.
3. **Hybrid construction.** Define the exact PDF byte ranges, files/states,
   message transformations, signatures and verification predicate. Include
   the nesting diagram and distinguish covered content from excluded fields.
4. **System design and implementation.** Describe snapshotting and atomic
   publication, key ID and vault trust boundaries, native worker/UI
   separation and platform profile. Attribute inherited messages and
   trailer layout to the original project.
5. **Experimental methodology.** Document the inherited source audit and
   Phase 5.2's independent controls, input generation, instrumentation,
   environment and statistical plan. Mark which comparators were implemented.
6. **Results and discussion.** Present inherited descriptive results
   separately from current functional evidence and newly collected
   experimental measurements. Discuss competing overheads and uncertainty.
7. **Security, implementation and deployment limits.** Discuss the
   encoding-equivalence question, adversary assumptions, key substitution,
   password limits and lack of signer identity, trusted time and
   interoperable PDF signatures. Bound all statements to observed evidence.
8. **Conclusion and future work.** Answer each question at its evidence level.
   Outline conformance, interoperability, formal analysis and trust lifecycle
   work left open.

| Contribution | Attribution |
| --- | --- |
| Original FALCON/eSign | Nested order, exact signed-message construction, custom signature format, original software and experimental CSV/PDF corpus. Cite the original authors and inherited commit. [Provenance](PROJECT_PROVENANCE.md) · [Original software citation](../CITATION.cff) |
| Thesis development before Phase 5.1 | Baseline/regression tests, strict verification and atomic writer, validated in-memory keys, encrypted local vault, native bridge/UI and packaging acceptance. It continues the inherited protocol. [Protocol hardening](phase2b3-regression.md) · [Vault signing](phase3-2b3-regression.md) · [Desktop release](phase4c3-final-release-review.md) |
| This phase | Independent inspection, descriptive recomputation from historical rows, source and test traceability, and a protocol proposal. Existing CSVs remain inherited measurements. |
| Future thesis work | Independent instrumented measurements, approved comparison adapters if needed, conformance checks and a decision on stronger claims. [Phase 5.2 plan](phase5-1-experiment-gap-analysis.md#phase-52-protocol) |

## Open academic decisions

- Confirm whether the supervisor expects a theoretical reference to Falcon
  v1.2 or an empirical claim about conformance to a specified encoding.
- Decide whether the thesis scope requires standalone PDF workflow
  comparators or is satisfied by matched primitive/stage costs and the real
  end-to-end hybrid pipeline.
- Ask the original study's authors whether June capture logs, exact library
  builds, signed samples or machine metadata survive. State missing provenance
  explicitly if those records cannot be obtained.
- Decide with the supervisor whether the native encoding-equivalence question
  and formal security model are research limitations or new evaluation
  objectives requiring a separate compatibility review.
- Align the final outline and any appendix/data deposit obligations to the
  actual university guidance when available.
