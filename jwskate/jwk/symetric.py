import secrets
from typing import Any, Iterable, List, Optional, Tuple, Union

from binapy import BinaPy

from jwskate.jwa import (
    A128GCM,
    A128KW,
    A192GCM,
    A192KW,
    A256GCM,
    A256KW,
    HS256,
    HS384,
    HS512,
    Aes128CbcHmacSha256,
    Aes192CbcHmacSha384,
    Aes256CbcHmacSha512,
    DirectKeyUse,
)

from ..jwa.key_mgmt import A128GCMKW, A192GCMKW, A256GCMKW
from ..jwa.key_mgmt.aeskw import AesKeyWrap
from .alg import select_alg, select_algs
from .base import Jwk, JwkParameter
from .exceptions import UnsupportedAlg


class SymmetricJwk(Jwk):
    """
    Implement Symetric keys, with `kty=oct`.
    """

    kty = "oct"

    PARAMS = {
        "k": JwkParameter("Key Value", is_private=True, is_required=True, kind="b64u"),
    }

    SIGNATURE_ALGORITHMS = {sigalg.name: sigalg for sigalg in [HS256, HS384, HS512]}

    KEY_MANAGEMENT_ALGORITHMS = {
        keyalg.name: keyalg
        for keyalg in [
            A128KW,
            A192KW,
            A256KW,
            A128GCMKW,
            A192GCMKW,
            A256GCMKW,
            DirectKeyUse,
        ]
    }

    ENCRYPTION_ALGORITHMS = {
        keyalg.name: keyalg
        for keyalg in [
            Aes128CbcHmacSha256,
            Aes192CbcHmacSha384,
            Aes256CbcHmacSha512,
            A128GCM,
            A192GCM,
            A256GCM,
        ]
    }

    def public_jwk(self) -> "Jwk":
        raise ValueError("Symmetric keys don't have a public key")

    @classmethod
    def from_bytes(cls, k: Union[bytes, str], **params: str) -> "SymmetricJwk":
        """
        Initializes a SymmetricJwk from a raw secret key.
        The provided secret key is encoded and used as the `k` parameter for the returned SymetricKey.
        :param k: the key to use
        :param params: additional parameters for the returned Jwk
        :return: a SymmetricJwk
        """
        return cls(dict(kty="oct", k=BinaPy(k).encode_to("b64u").decode(), **params))

    @classmethod
    def generate(cls, size: int = 128, **params: str) -> "SymmetricJwk":
        """
        Generates a random SymmetricJwk, with a given key size.
        :param size: the size of the generated key, in bytes.
        :param params: additional parameters for the returned Jwk
        :return: a SymmetricJwk with a random key
        """
        key = secrets.token_bytes(size // 8)
        return cls.from_bytes(key, **params)

    @classmethod
    def generate_for_alg(cls, alg: str, **params: str) -> "SymmetricJwk":
        if alg in cls.SIGNATURE_ALGORITHMS:
            sigalg = cls.SIGNATURE_ALGORITHMS[alg]
            return cls.generate(sigalg.min_key_size, alg=alg, **params)
        if alg in cls.ENCRYPTION_ALGORITHMS:
            encalg = cls.ENCRYPTION_ALGORITHMS[alg]
            return cls.generate(encalg.key_size, alg=alg, **params)
        raise ValueError("Unsupported alg", alg)

    def to_cryptography_key(self) -> Any:
        return self.key

    @property
    def key(self) -> bytes:
        """
        Returns the raw symmetric key.
        :return: the key from the `k` parameter, base64u-decoded.
        """
        return BinaPy(self.k).decode_from("b64u")

    @property
    def key_size(self) -> int:
        return len(self.key) * 8

    def sign(self, data: bytes, alg: Optional[str] = None) -> BinaPy:
        sigalg = select_alg(self.alg, alg, self.SIGNATURE_ALGORITHMS)

        m = sigalg.mac(self.key, sigalg.hash_alg)
        m.update(data)
        signature = m.finalize()
        return BinaPy(signature)

    def verify(
        self,
        data: bytes,
        signature: bytes,
        alg: Optional[str] = None,
        algs: Optional[Iterable[str]] = None,
    ) -> bool:
        for sigalg in select_algs(self.alg, alg, algs, self.SIGNATURE_ALGORITHMS):
            m = sigalg.mac(self.key, sigalg.hash_alg)
            m.update(data)
            candidate_signature = m.finalize()
            if signature == candidate_signature:
                return True

        return False

    def encrypt(
        self,
        plaintext: bytes,
        aad: Optional[bytes] = None,
        alg: Optional[str] = None,
        iv: Optional[bytes] = None,
    ) -> Tuple[BinaPy, BinaPy, BinaPy]:
        encalg = select_alg(self.alg, alg, self.ENCRYPTION_ALGORITHMS)

        if iv is None:
            iv = secrets.token_bytes(encalg.iv_size)

        wrapper = encalg(self.key)
        ciphertext_with_tag = wrapper.encrypt(iv, plaintext, aad)
        ciphertext = ciphertext_with_tag[: -encalg.tag_size]
        tag = ciphertext_with_tag[-encalg.tag_size :]

        return BinaPy(ciphertext), BinaPy(tag), BinaPy(iv)

    def decrypt(
        self,
        ciphertext: bytes,
        tag: bytes,
        iv: bytes,
        aad: Optional[bytes] = None,
        alg: Optional[str] = None,
    ) -> BinaPy:
        encalg = select_alg(self.alg, alg, self.ENCRYPTION_ALGORITHMS)

        if self.key_size != encalg.key_size:
            raise ValueError(
                f"This key size of {self.key_size} doesn't match the expected keysize for {encalg.name} of {encalg.key_size} bits"
            )

        decryptor = encalg(self.key)
        ciphertext_with_tag = ciphertext + tag
        plaintext: bytes = decryptor.decrypt(iv, ciphertext_with_tag, aad)

        return BinaPy(plaintext)

    def wrap_key(self, plainkey: bytes, alg: Optional[str] = None) -> BinaPy:
        keyalg = select_alg(self.alg, alg, self.KEY_MANAGEMENT_ALGORITHMS)
        wrapper = keyalg(self.to_cryptography_key())
        if isinstance(wrapper, AesKeyWrap):
            cipherkey = wrapper.wrap_key(plainkey)
        else:
            raise UnsupportedAlg(keyalg)
        return BinaPy(cipherkey)

    def unwrap_key(self, cipherkey: bytes, alg: Optional[str] = None) -> Jwk:
        keyalg = select_alg(self.alg, alg, self.KEY_MANAGEMENT_ALGORITHMS)
        wrapper = keyalg(self.key)
        if isinstance(wrapper, AesKeyWrap):
            plaintext = wrapper.unwrap_key(cipherkey)
        else:
            raise UnsupportedAlg(keyalg)
        return SymmetricJwk.from_bytes(plaintext)

    def supported_key_management_algorithms(self) -> List[str]:
        return [
            name
            for name, alg in self.KEY_MANAGEMENT_ALGORITHMS.items()
            if alg.supports_key(self.key)  # type: ignore
        ]

    def supported_encryption_algorithms(self) -> List[str]:
        return [
            name
            for name, alg in self.ENCRYPTION_ALGORITHMS.items()
            if alg.supports_key(self.key)
        ]
