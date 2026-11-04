from pqcrypto.sign import falcon_512
from nacl.signing import SigningKey
from hybrid_keys import HybridKeyPair, HybridPublicKey


def generate_hybrid_key_pair() -> HybridKeyPair:
    """Generate and self-test both key pairs without any private-key file I/O."""
    ed = SigningKey.generate()
    falcon_public, falcon_private = falcon_512.generate_keypair()
    return HybridKeyPair(HybridPublicKey(bytes(ed.verify_key), falcon_public),
                         ed.encode(), falcon_private)

def generate_keys(pk_ed: str , sk_ed: str, pk_falcon: str, sk_falcon: str):
    """Legacy explicit plaintext export; use generate_hybrid_key_pair() for RAM.

    Generation/validation finishes before writing, but the four-file export
    remains non-transactional and is not secure private-key storage.
    """
    pair = generate_hybrid_key_pair()

    with open(pk_ed, "wb") as f:
        f.write(pair.public_keys.ed25519_public_key)
    
    with open(sk_ed, "wb") as f:
        f.write(pair.ed25519_private_seed)

    with open(pk_falcon, "wb") as f:
        f.write(pair.public_keys.falcon_public_key)
    
    with open(sk_falcon, "wb") as f:
        f.write(pair.falcon_private_key)
