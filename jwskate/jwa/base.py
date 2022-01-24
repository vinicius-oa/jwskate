from contextlib import contextmanager
from typing import Generic, Iterator, Optional, Tuple, Type, TypeVar, Union

from binapy import BinaPy


class Alg:
    """
    Base class for all algorithms.

    An algorithm has a name and a description, whose reference is here: https://www.iana.org/assignments/jose/jose.xhtml#web-signature-encryption-algorithms
    """

    name: str
    description: str
    read_only: bool = False

    def __str__(self) -> str:
        return self.name


class SymmetricAlg(Alg):
    """
    Base class for Symmetric algorithms (using a raw bytes key).
    """

    def __init__(self, key: bytes):
        """
        Initialize a Symmetric alg with a given key.
        :param key: the key to use for cryptographic operations.
        """
        self.check_key(key)
        self.key = key

    @classmethod
    def check_key(cls, key: bytes) -> None:
        """
        Check that a given key is suitable for this alg class.

        This raises an exception if the key is not suitable.
        :param key: the key to check for this alg class.
        :return: None. Raises an exception if the key is not suitable.
        """
        pass

    @classmethod
    def supports_key(cls, key: bytes) -> bool:
        """
        Return `True` if the given key is suitable for this alg class, or `False` otherwise.

        This is a convenience wrapper around `check_key(key)`.
        :param key: the key to check for this alg class.
        :return: `True` if the key is suitable for this alg class, `False` otherwise.
        """
        try:
            cls.check_key(key)
            return True
        except Exception:
            return False


Kpriv = TypeVar("Kpriv")
Kpub = TypeVar("Kpub")


class PrivateKeyRequired(AttributeError):
    """
    Raised when a cryptographic operation requires a private key, and a public key has been provided instead.
    """

    pass


class PublicKeyRequired(AttributeError):
    """
    Raised when a cryptographic operation requires a public key, and a private key has been provided instead.
    """

    pass


class AsymmetricAlg(Generic[Kpriv, Kpub], Alg):
    """
    Base class for asymmetric algorithms. Those can be initialised with a private or public key.

    The available cryptographic operations will depend on the alg and the provided key type.
    """

    private_key_class: Union[Type[Kpriv], Tuple[Type[Kpriv], ...]]
    public_key_class: Union[Type[Kpub], Tuple[Type[Kpub], ...]]

    def __init__(self, key: Union[Kpriv, Kpub]):
        """
        Initialise an Asymmetric alg with either a private or a public key.
        :param key: the key to use.
        """
        self.check_key(key)
        self.key = key

    @classmethod
    def check_key(cls, key: Union[Kpriv, Kpub]) -> None:
        """
        Check that a given key is suitable for this alg class.
        :param key: the key to use.
        :return: None. Raises an exception if the key is not suitable.
        """

    @classmethod
    def supports_key(cls, key: Union[Kpriv, Kpub]) -> bool:
        """
        Return `True` if the given key is suitable for this alg class, or `False` otherwise.

        This is a convenience wrapper around `check_key(key)`.
        :param key: the key to check for this alg class.
        :return: `True` if the key is suitable for this alg class, `False` otherwise.
        """
        try:
            cls.check_key(key)
            return True
        except Exception:
            return False

    @contextmanager
    def private_key_required(self) -> Iterator[Kpriv]:
        """
        A context manager that checks if this alg is initialised with a private key.
        :return: the private key
        """
        if not isinstance(self.key, self.private_key_class):
            raise PrivateKeyRequired()
        yield self.key  # type: ignore

    @contextmanager
    def public_key_required(self) -> Iterator[Kpub]:
        """
        A context manager that checks if this alg is initialised with a public key
        :return: the public key
        """
        if not isinstance(self.key, self.public_key_class):
            raise PublicKeyRequired()
        yield self.key  # type: ignore


class SignatureAlg(Alg):
    """
    Base class for signature algs.
    """

    def sign(self, data: bytes) -> BinaPy:
        """
        Sign arbitrary data, return the signature.
        :param data: raw data to sign.
        :return: the raw signature.
        """
        raise NotImplementedError

    def verify(self, data: bytes, signature: bytes) -> bool:
        """
        Verify a signature against arbitrary data.
        :param data: the raw data to verify.
        :param signature: the raw signature.
        :return: `True` if the signature matches, `False` otherwise.
        """
        raise NotImplementedError


class AESAlg(SymmetricAlg):
    """
    Base class for AES encryption algorithms.
    """

    key_size: int
    tag_size: int
    iv_size: int

    @classmethod
    def check_key(cls, key: bytes) -> None:
        if cls.key_size is not None and len(key) * 8 != cls.key_size:
            raise ValueError(
                f"This key size of {len(key) * 8} bits doesn't match the expected keysize of {cls.key_size} bits"
            )

    def encrypt(self, iv: bytes, plaintext: bytes, aad: Optional[bytes]) -> BinaPy:
        """
        Encrypt arbitrary data (plaintext) with the given Initialisation Vector (iv)
        and optional Additional Authentication Data (aad), returns the ciphered text.
        :param iv: the Initialisation Vector to use.
        :param plaintext: the data to encrypt
        :param aad: the Additional Authentication Data
        :return: the ciphered data.
        """
        raise NotImplementedError

    def decrypt(self, iv: bytes, ciphertext: bytes, aad: Optional[bytes]) -> BinaPy:
        """
        Decrypt a ciphertext with a given Initialisation Vector (iv)
        and optional Additional Authentication Data (aad), returns the resulting clear text.
        :param iv: the Initialisation Vector to use. Must be the same one used during encryption.
        :param ciphertext: the encrypted data.
        :param aad: the Additional Authentication Data. Must be the same one used during encryption.
        :return: the deciphered data
        """
        raise NotImplementedError


class KeyManagementAlg(Alg):
    """
    Base class for Key Management algorithms.
    """
