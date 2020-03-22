import gzip
import zlib
import pathlib
import hashlib
from contextlib import suppress
from dataclasses import dataclass
from Cryptodome.Cipher import AES
from .utils import threaded


@dataclass
class WhatsAppCrypt:
    input_file: pathlib.Path
    key_file: pathlib.Path = None
    email: str = None

    GZIP_MAGIC = b'\x1f\x8b\x08'
    SQLITE_MAGIC = b'SQLite format 3\x00'
    KEY_SIZE = 158
    SUFFIX = '.decoded.db'

    def __post_init__(self):
        self.fname = self.input_file.name
        self.input_data = None
        self.KEY = None
        self.IV = None

    @property
    def dst(self):
        return self.input_file.with_suffix(self.SUFFIX)

    def get_key(self):
        with self.key_file.open('rb') as R:
            self.KEY = R.read()[126:158]

    def get_iv(self, iv_from_file=False):
        if iv_from_file:
            with self.input_file.open('rb') as R:
                self.IV = R.read()[51:67]
        else:
            with self.key_fileopen('rb') as R:
                self.IV = R.read()[110:126]

    def aes_0(self):
        # 346a23652a46392b4d73257c67317e352e3372482177652c
        return AES.new(b'4j#e*F9+Ms%|g1~5.3rH!we,')

    def aes_5(self):
        ACC = hashlib.md5(self.email.encode()).digest()
        KEY = bytearray(b'\x8dK\x15\\\xc9\xff\x81\xe5\xcb\xf6\xfax\x196j>\xc6!\xa6VAl\xd7\x93')
        for i in range(24):
            KEY[i] ^= ACC[i]
        IV = b'\x1e9\xf3i\xe9\r\xb3:\xa7;D+\xbb\xb6\xb0\xb9'
        return AES.new(bytes(KEY), AES.MODE_CBC, IV)

    def aes_7(self, mode=AES.MODE_CBC, iv_from_file=False):
        self.get_key()
        self.get_iv(iv_from_file=iv_from_file)
        return AES.new(self.KEY, mode, self.IV)

    def aes_8(self, mode=AES.MODE_CBC, iv_from_file=True):
        self.get_key()
        self.get_iv(iv_from_file=iv_from_file)
        return AES.new(self.KEY, mode, self.IV)

    def aes_9(self, mode=AES.MODE_GCM, iv_from_file=True):
        self.get_key()
        self.get_iv(iv_from_file=iv_from_file)
        return AES.new(self.KEY, mode, self.IV)

    def aes_10(self, mode=AES.MODE_GCM, iv_from_file=True):
        self.get_key()
        self.get_iv(iv_from_file=iv_from_file)
        return AES.new(self.KEY, mode, self.IV)

    def aes_12(self, mode=AES.MODE_GCM, iv_from_file=True):
        self.get_key()
        self.get_iv(iv_from_file=iv_from_file)
        return AES.new(self.KEY, mode, self.IV)

    @staticmethod
    def unpad_pkcs5(data, bs=16):
        if len(data) % bs == 0:
            return data
        elif 0 < data[-1] > bs:
            return data[0:-(len(data) % bs)]
        else:
            return data[0:-data[-1]]

    @staticmethod
    def unpad(data):
        return data[0:-data[-1]]

    def check_input_file_size(self, head_size=67):
        if not (self.input_file.stat().st_size - head_size) % 16 == 0:
            raise WhatsAppCryptError('Unexpected input file size, may not be decrypted.')

    def check_input_data_size(self, data, head_size=67):
        if not (len(data) - head_size) % 16 == 0:
            raise WhatsAppCryptError('Unexpected input file size, may not be decrypted.')

    def check_key_file_size(self):
        if not self.key_file.stat().st_size == self.KEY_SIZE:
            raise WhatsAppCryptError('Odd key file size.')

    @classmethod
    def check_is_sqlite(cls, data):
        if not data.startswith(cls.SQLITE_MAGIC):
            raise WhatsAppCryptError('Decryption failed (not sqlite).')

    @classmethod
    def check_is_gzip(cls, data):
        if not data.startswith(cls.GZIP_MAGIC):
            raise WhatsAppCryptError('Decryption failed (not gzip).')

    def gzip_decompress(self, data):
        # Python gzip lib bug workaround
        length = len(data)
        for i in range(0, -65, -1):
            i = length if not i else i
            with suppress(OSError):
                return gzip.decompress(data[:i])
        raise WhatsAppCryptError('Decompression failed')

    @threaded
    def decrypt(self, **kwargs):
        # self.check_input_file_size(**kwargs)
        self.check_key_file_size()
        self.input_data = self.input_file.read_bytes()

    def save_output(self, data):
        if self.dst.is_file():
            raise WhatsAppCryptError(f'File {self.dst} already exists!')
        self.dst.write_bytes(data)


# -----------------------------------------------------------------------------
class WhatsAppCrypt7(WhatsAppCrypt):
    CRYPT = 'crypt7'

    def __init__(self, input_file, key_file):
        super().__init__(input_file=input_file, key_file=key_file)

    def decrypt(self, **kwargs):
        super().decrypt(**kwargs)
        data = self.aes_7.decrypt(self.input_data[67:])
        self.check_is_sqlite(data)
        self.save_output(data)
        return self.dst


class WhatsAppCrypt8(WhatsAppCrypt):
    CRYPT = 'crypt8'

    def __init__(self, input_file, key_file):
        super().__init__(input_file=input_file, key_file=key_file)

    def decrypt(self, **kwargs):
        super().decrypt(**kwargs)
        cipher = self.aes_8()
        data = cipher.decrypt(self.input_data[67:])
        self.check_is_gzip(data)
        data = gzip.decompress(self.unpad(data))
        self.check_is_sqlite(data)
        self.save_output(data)
        return self.dst


class WhatsAppCrypt9(WhatsAppCrypt):
    CRYPT = 'crypt9'

    def __init__(self, input_file, key_file):
        super().__init__(input_file=input_file, key_file=key_file)

    def decrypt(self, **kwargs):
        super().decrypt(**kwargs)
        data = self.unpad_pkcs5(self.input_data[67:])
        self.check_input_data_size(data, head_size=0)
        cipher = self.aes_9()
        data = cipher.decrypt(data)
        data = self.gzip_decompress(data)
        self.check_is_sqlite(data)
        self.save_output(data)
        return self.dst


class WhatsAppCrypt10(WhatsAppCrypt9, WhatsAppCrypt):
    CRYPT = 'crypt10'


class WhatsAppCrypt11(WhatsAppCrypt9, WhatsAppCrypt):
    CRYPT = 'crypt11'


class WhatsAppCrypt12(WhatsAppCrypt):
    CRYPT = 'crypt12'

    def __init__(self, input_file, key_file):
        super().__init__(input_file, key_file=key_file)

    def decrypt(self, **kwargs):
        super().decrypt(**kwargs)
        data = self.unpad_pkcs5(self.input_data[67:])
        self.check_input_data_size(data, head_size=0)
        cipher = self.aes_12()
        data = cipher.decrypt(data)
        data = zlib.decompress(data)
        self.check_is_sqlite(data)
        self.save_output(data)
        return self.dst


# -----------------------------------------------------------------------------

class WhatsAppCryptError(Exception):
    pass
