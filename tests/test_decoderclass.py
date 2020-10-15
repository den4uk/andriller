import os
import pytest
import hashlib
import tempfile
from andriller.classes import AndroidDecoder, DecoderError
from .test_config import conf


class Decodr(AndroidDecoder):
    TARGET = 'data.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.myapp'
    template_name = 'test_messages.html'
    title = 'Test Messages'
    headers = {
        '_id': 'Index',
        'name': 'Name',
        'number': 'Number',
        'message': 'Message',
        'timestamp': 'Time',
        'status': 'status',
        'type': 'type',
        'duration': 'duration',
    }

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.add_extra('f', 'some.xml')

    def main(self):
        pass


@pytest.fixture
def Deco(conf):
    work_dir = tempfile.TemporaryDirectory()
    input_file = tempfile.NamedTemporaryFile()
    dec = Decodr(work_dir.name, input_file.name)
    return dec


@pytest.fixture
def DecoTZ(conf):
    conf.update_conf(**{conf.NS: {'time_zone': 'UTC-05:00'}})
    work_dir = tempfile.TemporaryDirectory()
    input_file = tempfile.NamedTemporaryFile()
    dec = Decodr(work_dir.name, input_file.name)
    return dec


@pytest.fixture
def DecoFile(Deco):
    # TODO: use a db with -wal / -journal
    # Make sure the files still exist after the test
    Deco.input_file = os.path.join(os.path.dirname(__file__),
        'data', 'other', 'locks', 'locksettings.db')
    return Deco


def test_input_path_no_change(Deco):
    assert Deco.input_file.endswith('some.xml') is False


def test_paths(Deco):
    assert Deco.target_path_ab == 'apps/com.myapp/db/data.db'
    assert Deco.target_path_root == '/data/data/com.myapp/databases/data.db'
    assert Deco.target_path_posix == 'com.myapp/*/data.db'


def test_extra_paths(Deco):
    extras = Deco.get_extras()
    assert '/data/data/com.myapp/files/some.xml' in extras


def test_init_data(Deco):
    assert Deco.title == 'Test Messages'


def test_read_only_sqlite_path(DecoFile):
    assert os.path.exists(DecoFile.input_file)
    assert DecoFile.sqlite_readonly.endswith('?mode=ro')


def test_sqlite_read_only_hash_file(DecoFile):
    file_parts = ['', '-wal']
    file_hashes = ['1e6481eed041176e4cc05bfc55c09314', 'a29c5927d6db20b446f04d891d639709']

    for table in DecoFile.get_sql_tables():
        [*DecoFile.sql_table_as_dict(table)]
        [*DecoFile.get_table_columns(table)]
        [*DecoFile.sql_table_rows(table)]

    test_hashes = []
    for f in file_parts:
        with open(DecoFile.input_file + f, 'rb') as R:
            test_hashes.append(hashlib.md5(R.read()).hexdigest())
    assert test_hashes == file_hashes


@pytest.mark.parametrize('params, result', [
    ({'!status': 6, 'status': [1, 2]}, "NOT status='6' AND (status='1' OR status='2')"),
    ({'type': ['lol', 'rolf'], '!status': [100]}, "(type='lol' OR type='rolf') AND (NOT status='100')"),
    ({'status': 1}, "status='1'"),
    ({'!status': 0}, "NOT status='0'"),
    ({}, ''),
])
def test_where(Deco, params, result):
    assert Deco.where(params) == result


@pytest.mark.parametrize('data, result', [
    (0, '00:00:00'),
    (1, '00:00:01'),
    (60, '00:01:00'),
    (3600, '01:00:00'),
])
def test_duration(Deco, data, result):
    assert Deco.duration(data) == result


@pytest.mark.parametrize('data, result', [
    ('', ''),
    (None, ''),
    ('jkhfejwkfhwejk', 'jkhfejwkfhwejk'),
    (b'98wefewhg', '98wefewhg'),
])
def test_to_chars(Deco, data, result):
    assert Deco.to_chars(data) == result


def test_check_magic_error(DecoFile):
    DecoFile.input_file += '_boom'
    with pytest.raises(DecoderError):
        DecoFile.check_sqlite_magic()


def test_unix_to_time(Deco):
    assert Deco.unix_to_time(1555711540) == '2019-04-19 22:05:40 UTC'


def test_unix_to_time_ms_tz(DecoTZ):
    assert DecoTZ.unix_to_time_ms(1555711540123) == '2019-04-19 17:05:40 UTC-05:00'


@pytest.mark.parametrize('data, result', [
    (0, 0),
    (-23, -23),
    (42, 42),
    (3.14, 3.14),
    (None, ''),
    ('foo', 'foo'),
    ('Технологии', 'Технологии'),
    ('paspauskite mygtuką „Sutinku“ arba naršykite', 'paspauskite mygtuką „Sutinku“ arba naršykite'),
    (b'\x20', ' '),
    ('\xe2\x98\x80\xef\xb8\x8f', '☀️')
])
def test_safe_str(Deco, data, result):
    Deco.safe_str(data) == result


def test_decoder_data_types(Deco):
    assert Deco.call_type(1) == 'Received'
    assert Deco.call_type(2) == 'Dialled'
    assert Deco.call_type(3) == 'Missed'
    assert 'Unknown' in Deco.call_type(-9)

    assert Deco.sms_type(1) == 'Inbox'
    assert Deco.sms_type(2) == 'Sent'
    assert 'Unknown' in Deco.sms_type(-9)

    assert Deco.skype_msg_type(2) == 'Sent'
    assert Deco.skype_msg_type(4) == 'Read'
    assert 'Unknown' in Deco.skype_msg_type(0)

    assert Deco.skype_call_type(5) == 'Incoming'
    assert Deco.skype_call_type(6) == 'Outgoing'
    assert 'Unknown' in Deco.skype_call_type(0)


@pytest.mark.parametrize('data, result', [
    ('+1 234 567', '+1234567'),
    ('Mark 079 876 543', 'Mark 079876543'),
    ('-1', 'UNKNOWN'),
    ('-2', 'WITHHELD'),
    ('', ''),
    (None, ''),
    (123, '123'),
])
def test_parse_number(Deco, data, result):
    assert Deco.parse_number(data) == result
