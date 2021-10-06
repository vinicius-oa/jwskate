from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Union

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed448, ed25519, x448, x25519

from ..utils import b64u_encode
from .base import Jwk


class OKPJwk(Jwk):
    """
    Represents an OKP Jwk (with `"kty": "OKP"`)
    """

    kty = "OKP"

    PARAMS = {
        "crv": ("Curve", False, True, "name"),
        "x": ("Public Key", False, True, "b64u"),
        "d": ("Private Key", True, False, "b64u"),
    }

    CURVES: Dict[str, Callable[[], Any]] = {
        # curve: generator
        "Ed25519": ed25519.Ed25519PrivateKey.generate,
        "Ed448": ed448.Ed448PrivateKey.generate,
        "X25519": x25519.X25519PrivateKey.generate,
        "X448": x448.X448PrivateKey.generate,
    }

    SIGNATURE_ALGORITHMS: Dict[str, Tuple[str, hashes.HashAlgorithm]] = {
        # name : (description, hash_alg)
    }

    @classmethod
    def public(cls, crv: str, x: str, **params: str) -> "OKPJwk":
        return cls(dict(crv=crv, x=x, **params))

    @classmethod
    def private(cls, crv: str, x: bytes, d: bytes, **params: str) -> "OKPJwk":
        return cls(dict(crv=crv, x=b64u_encode(x), d=b64u_encode(d), **params))

    @classmethod
    def generate(cls, crv: str, **params: str) -> "OKPJwk":
        generator = cls.CURVES.get(crv)
        if generator is None:
            raise ValueError("Unsupported Curve", crv)
        key = generator()
        x = key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        d = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return cls.private(crv=crv, x=x, d=d, **params)

    def sign(self, data: bytes, alg: Optional[str]) -> bytes:
        raise NotImplementedError

    def verify(
        self, data: bytes, signature: bytes, alg: Union[str, Iterable[str], None]
    ) -> bool:
        raise NotImplementedError

    def decrypt(
        self,
        cyphertext: bytes,
        tag: bytes,
        iv: bytes,
        aad: Optional[bytes] = None,
        alg: Optional[str] = None,
    ) -> bytes:
        raise NotImplementedError

    def encrypt(
        self,
        plaintext: bytes,
        aad: Optional[bytes] = None,
        alg: Optional[str] = None,
        iv: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes, bytes]:
        raise NotImplementedError

    def encrypt_key(self, key: bytes, alg: Optional[str] = None) -> bytes:
        raise NotImplementedError

    def decrypt_key(self, cypherkey: bytes, alg: Optional[str] = None) -> bytes:
        raise NotImplementedError
