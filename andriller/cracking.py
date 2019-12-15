import time
import struct
import string
import hashlib
import logging
import binascii
import itertools
from dataclasses import dataclass
from . import utils

logger = logging.getLogger(__name__)


def crack_pattern(pat: str) -> list:
    """
    Simple gesture key cracker.
    """
    patd = binascii.unhexlify(pat.strip())
    if patd == hashlib.sha1(b'').digest():
        return None
    vals = '\x00\x01\x02\x03\x04\x05\x06\x07\x08'
    for i in range(4, 10):
        for p in itertools.permutations(vals, i):
            combo = ''.join(p).encode()
            if hashlib.sha1(combo).digest() == patd:
                return list(combo)
    else:
        return False


class PasswordCrackError(Exception):
    pass


@dataclass
class PasswordCrack:
    key: str
    salt: int
    start: int = 0
    end: int = 9999
    min_len: int = None
    max_len: int = None
    alpha: bool = None
    dict_file: str = False
    alpha_range: str = None
    samsung: bool = False
    update_rate: int = 50000

    def __post_init__(self):
        self.key = self.get_hash(self.key)
        self.salt = self.get_salt(self.salt)
        self.current = None
        self.tried = 0
        self.rate = 0
        self.total = 0
        self.update_rate = (self.update_rate // 1024) if self.samsung else self.update_rate

    @staticmethod
    def get_hash(key: str) -> bytes:
        if not key or not utils.is_hex(key) or not (len(key) in [40, 72]):
            raise PasswordCrackError('Must enter HASH value.')
        return binascii.unhexlify(key[:40])

    @staticmethod
    def get_salt(salt: int) -> bytes:
        if not salt:
            raise PasswordCrackError('Must enter SALT value as integer')
        if not isinstance(salt, int):
            raise PasswordCrackError('Salt must be an integer')
        return (
            f'{salt:x}'.encode()
            if salt > 0
            else binascii.hexlify(struct.pack(">q", salt))
        )

    @staticmethod
    def int_to_bytes(i: int) -> bytes:
        return f'{i}'.encode()

    @staticmethod
    def make_pin(pin: tuple, length: int) -> bytes:
        return ''.join(pin).zfill(length).encode()

    def _sam_algo(self, pin: bytes, times=1024) -> bytes:
        base = hashlib.sha1(b'0' + pin + self.salt).digest()
        for i in map(self.int_to_bytes, range(1, times)):
            base = hashlib.sha1(base + i + pin + self.salt).digest()
        return base

    def _gen_algo(self, pin: bytes) -> bytes:
        return hashlib.sha1(pin + self.salt).digest()

    def _feed_pins(self):
        for length in range(4, len(str(self.end)) + 1):
            for pin in map(
                lambda x: self.make_pin(x, length),
                itertools.product(string.digits, repeat=length),
            ):
                yield pin

    def _feed_alpha(self):
        if not self.alpha_range:
            raise PasswordCrackError('Range of characters not specified')
        for i in range(self.min_len, self.max_len + 1):
            for prod in itertools.product(self.alpha_range, repeat=i):
                yield ''.join(prod).encode()

    def _feed_dict(self):
        with open(self.dict_file, 'rb') as R:
            for w in R:
                yield w.rstrip()

    def _get_feed(self):
        if not self.alpha:
            return self._feed_pins()
        elif self.dict_file:
            return self._feed_dict()
        elif self.alpha_range:
            return self._feed_alpha()
        else:
            raise PasswordCrackError('Attack method was not chosen.')

    def get_total_combos(self):
        return sum(
            len(self.alpha_range) ** i for i in range(self.min_len, self.max_len + 1)
        )

    @staticmethod
    def set_tried(obj, n):
        if obj:
            obj.set(f'{n:,}')

    def set_rate(self, obj, n, started):
        if obj:
            self.rate = int(n / (time.time() - started))
            obj.set(f'{self.rate: ,}')

    def set_prog(self, obj, n, total):
        if obj:
            done_ = n / total * 100
            rem_ = utils.human_time((total - n) // self.rate)
            obj.set(f'{done_:,.2f} % \t{rem_} reamining')

    def crack_password(self, tk_obj=None, stop=None, tried=None, rate=None, prog=None):
        algo = self._gen_algo if not self.samsung else self._sam_algo
        feed = self._get_feed()
        if prog:
            self.total = self.get_total_combos()
        started = time.time()
        n = 0
        for n, pin in enumerate(feed, start=1):
            if not n % self.update_rate and tk_obj:
                self.set_rate(rate, n, started)
                self.set_tried(tried, n)
                self.set_prog(prog, n, self.total)
                tk_obj.set(pin.decode())
                if stop and stop.get():
                    break
            if algo(pin) == self.key:
                self.set_tried(tried, n)
                return pin.decode()
        self.set_tried(tried, n)
