# Falcon implementation evidence for Phase 3.1

This investigation identifies the existing implementation; it does not upgrade
the dependency, rebuild native code or certify conformance to a specification.
No dependencies were installed. Published archives were inspected in memory,
without extracting or installing their contents.

## Installed implementation and release artifact

The existing Windows x64 Python 3.11.9 environment contains `pqcrypto==0.3.4`.
`pqcrypto/sign/falcon_512.py` imports `pqcrypto._sign.falcon_512` and uses
`PQCLEAN_FALCON512_CLEAN` entry points. The loaded native extension is
`falcon_512.cp311-win_amd64.pyd`.

| Observation | Value |
| --- | --- |
| Algorithm identifier | `falcon_512` |
| Public key size | 897 bytes |
| Secret key size | 1281 bytes |
| Maximum detached signature size | 752 bytes; actual signatures are variable-length |
| Published wheel | `pqcrypto-0.3.4-cp311-cp311-win_amd64.whl` |
| Wheel SHA256 | `36ec272e32d24cd137fd937bf218d0c86f4b0d5d17ed26828708e1a71b667380` |
| Installed wrapper SHA256 | `ef1acb5f04592c0c8bea1f11b32478216cf499d66d27f91232094daee23d2f4b` |
| Loaded native extension SHA256 | `ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237` |

Downloaded the wheel specified by the official [PyPI 0.3.4 release metadata](https://pypi.org/pypi/pqcrypto/0.3.4/json),
verified its SHA256 against that metadata, and compared its wrapper and native
extension bytes with the installed files: both match exactly. The release
metadata listed wheels and no source distribution at the time of inspection.

Matching the published wheel establishes the artifact checked here, not that
its native build is independently reproducible or free of implementation bugs.

## Source-lineage evidence

1. PyPI's [published wheel provenance](https://pypi.org/integrity/pqcrypto/0.3.4/pqcrypto-0.3.4-cp311-cp311-win_amd64.whl/provenance)
   names the wheel/digest above. Its attestation certificate contains repository
   commit `4d35e96a3a921f6a0907fcbce31f441c11e2de8d` for `backbone-hq/pqcrypto`.
   The certificate/statement fields were inspected, but the Sigstore certificate
   chain, signatures and transparency proofs were **not independently verified**.
2. That commit's [project metadata](https://github.com/backbone-hq/pqcrypto/blob/4d35e96a3a921f6a0907fcbce31f441c11e2de8d/pyproject.toml)
   identifies version 0.3.4. Its build configuration runs `compile.py`; the
   [compiler script](https://github.com/backbone-hq/pqcrypto/blob/4d35e96a3a921f6a0907fcbce31f441c11e2de8d/compile.py)
   selects the `clean` variant. Its [CI workflow](https://github.com/backbone-hq/pqcrypto/blob/4d35e96a3a921f6a0907fcbce31f441c11e2de8d/.github/workflows/ci.yml)
   checks out submodules before building wheels.
3. The [pinned submodule entry](https://api.github.com/repos/backbone-hq/pqcrypto/contents/pqclean?ref=4d35e96a3a921f6a0907fcbce31f441c11e2de8d)
   points to PQClean commit `2cc64716044832eea747234ddbffc06746ab815d`.
4. That revision's [Falcon-512 metadata](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/META.yml)
   labels the clean implementation **20211101 with PQClean patches**. Its key
   sizes and maximum signature size match the installed binding. Its
   [native API](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/api.h)
   explicitly describes variable-length detached signatures; the
   [implementation wrapper](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/pqclean.c)
   supplies the corresponding encoding and detached-signature functions.

These are useful source-lineage observations, with the attestation verification
and binary/source reproducibility limits above. They are not a locally verified
build proof. No network dependency or provenance request was added to runtime
generation, signing, verification or tests.

## Relationship to the thesis's Falcon revision

The Falcon authors' [official specification](https://falcon-sign.info/falcon.pdf)
is explicitly labelled **Specification v1.2**, dated **01/10/2020** on its title
page. The [authors' website](https://falcon-sign.info/) also discusses the
2021-11-01 implementation API correction and states that the PQClean
implementations were not affected by that particular issue.

The specification version, an implementation's date/patch label and a Python
package version are different identifiers. Neither matching key sizes nor a
successful round trip proves conformance to every requirement of v1.2. The
repository's current thesis/provenance documentation does not supply a complete
thesis manuscript with which to establish the exact intended revision.

Recommended implementation wording:

> Falcon-512 through pqcrypto 0.3.4's PQClean clean binding, with the investigated
> source lineage labelled 20211101 with PQClean patches.

The official v1.2 specification can be cited separately as the algorithm's
reference document. Do not describe this work as an independently validated
Falcon-v1.2 implementation. A stronger claim needs verified build provenance,
specification/patch review and appropriate known-answer/interoperability tests.
The upstream metadata's KAT hashes were observed, not reproduced locally.

Phase 3.1 therefore retains the exact identifier `falcon_512`; it does not invent
`falcon-v1.2`, substitute `falcon_padded_512`, or claim FIPS 206/FN-DSA, CMS,
PAdES or production compliance. The application's external ASCII Contents
padding is separate from the native signature encoding and is still enforced
by the unchanged Phase 2 parser.
