import os
import re
import json
import uuid
import zlib
import string
import hashlib
import logging
import tarfile
import tempfile
import datetime
import threading
import functools
import contextlib

logger = logging.getLogger(__name__)


def placebo(*args, **kwargs):
    """
    Decorator that decorates nothing (used to replace real ones where functionality is not possible).
    """
    def decorate(function):
        return function
    return decorate


def threaded(method):
    """
    Send the function to be executed on a separate thread rather than the main thread.
    To be used inside a class only.
    If NOTHREAD is found in environment variables, defaults to the main thread.
    """
    if os.environ.get('NOTHREAD'):
        return method

    @functools.wraps(method)
    def func(self, *args, **kwargs):
        def command():
            return method(self, *args, **kwargs)
        threading.Thread(target=command).start()
    return func


def human_time(sec):
    return f'{str(datetime.timedelta(seconds=sec)):0>8}'


def human_bytes(size):
    if size < 0:
        return human_bytes(0)
    powers = {20: 'KB', 30: 'MB', 40: 'GB', 50: 'TB', 60: 'PB'}
    if size < (2 ** 10):
        return f'{size}'
    for pw, name in powers.items():
        if size in range(2 ** pw):
            return f'{round(size / (2 ** (pw - 10)), pw // 20)}{name}'


def totupe(ver: str) -> tuple:
    """
    Converts a semantic version to a tuple, eg: '1.2.3' -> (1, 2, 3)
    """
    res = re.match(r'^(?:\d\.?)+', ver.strip()).group()
    return tuple(map(int, res.split('.')))


def is_uuid(data):
    with contextlib.suppress(Exception):
        if isinstance(data, uuid.UUID):
            return data
        return uuid.UUID(data)
    return False


def is_hex(data: str) -> bool:
    return all(c in string.hexdigits for c in data)


def get_koi(payload, keys: list) -> dict:
    """
    Get keys of interest from a JSON-like object
    Flattens the object and gets values for keys
    """
    # Cleanup the object
    if payload and type(payload) == str:
        try:
            payload = re.sub('\n', '', payload)
            return get_koi(json.loads(payload), keys)
        except Exception:
            return {}

    targets = [str, int, float, bool]
    result = {k: None for k in keys}

    def process(payload):
        if isinstance(payload, dict):
            for k, v in payload.items():
                if type(v) in targets:
                    if k in keys:
                        result[k] = v
                else:
                    process(v)
        elif isinstance(payload, list):
            for i in payload:
                process(i)

    if payload and type(payload) in [list, dict]:
        process(payload)
    return result if set(result.values()) else {}


def hash_file(file_path, algo='md5', buff=2**20):
    hasher = hashlib.new(algo)
    with open(f'{file_path}.{algo}', 'w') as W:
        with open(file_path, 'rb') as R:
            while True:
                d = R.read(buff)
                if not d:
                    break
                hasher.update(d)
        W.write(hasher.hexdigest())
    return hasher.hexdigest()


# -----------------------------------------------------------------------------
class DrillerTools:
    AB_MAGIC = b'ANDROID BACKUP'

    @classmethod
    def ab_file_verify(cls, file_obj):
        """
        Checks the file magic and whether the file is encrypted
        """
        if file_obj.read(len(cls.AB_MAGIC)) != cls.AB_MAGIC:
            raise DrillerError('Not an Android backup file!')
        type_ = file_obj.read(4)
        if type_ == b'AES-':
            # TODO: add support to encrypted backups
            raise DrillerError('AB file is encrypted.')
        elif type_ == b'none':
            pass

    @classmethod
    def ab_to_tar(cls, input_file, to_tmp=True):
        """
        Takes AB file, and converts it to a tarball, return file path to tar
        If to_tmp is set to False, converts into same directory
        """
        BUFFER = 2 ** 20
        with open(input_file, 'rb') as backup_file:
            cls.ab_file_verify(backup_file)
            # TODO: make it responsive to encrypted backups
            backup_file.seek(24)
            temptar = tempfile.NamedTemporaryFile(delete=False, suffix='.tar') if \
                to_tmp else open(f'{input_file}.tar', 'wb')
            zlib_obj = zlib.decompressobj()
            while True:
                d = backup_file.read(BUFFER)
                if not d:
                    break
                c = zlib_obj.decompress(d)
                temptar.write(c)
            zlib_obj.flush()
            temptar.close()
            return temptar.name

    @staticmethod
    def extract_form_tar(src_file, dst_dir, targets=[], full=False):
        """
        Yields tar file names, uses a list of targets or a full extraction
        """
        with tarfile.open(src_file) as tar:
            for tar_name in tar.getnames():
                try:
                    tar.extract(tar_name, dst_dir)
                    logger.debug(tar_name)
                    if tar_name in targets or full:
                        yield tar_name
                except Exception as err:
                    logger.warning(f'Failed extracting: {tar_name} > {err}')

    @staticmethod
    def extract_tar_members(src_file, dst_dir, match='.+?'):
        """
        Yields tar members, uses regex to identify files
        """
        rex = re.compile(match)
        with tarfile.open(src_file) as tar:
            for mem in tar.getmembers():
                if not rex.match(mem.path):
                    continue
                try:
                    tar.extract(mem, dst_dir)
                    yield mem
                except Exception as err:
                    logger.warning(f'Failed extracting: {mem} > {err}')


class DrillerError(Exception):
    pass
