import pytest
import uuid
import tempfile
from andriller import utils


@pytest.mark.parametrize('data', [
    uuid.uuid4(),
    '6f59e8ee-5343-4f11-b685-cfbe02bb9a12',
    '6f59e8ee53434f11b685cfbe02bb9a12',
    '6F59E8EE53434F11B685CFBE02BB9A12',
    '6-f-5-9-e-8-e-e-5-3-4-3-4-f-1-1-b-6-8-5-c-f-b-e-0-2-b-b-9-a-1-2',
    '6f59e8ee-53434f11-b685cfbe-02bb9a12',
    '6F59E8EE-53434F11-B685CFBE-02BB9A12',
])
def test_is_uuid_ok(data):
    assert type(utils.is_uuid(data)) == uuid.UUID


@pytest.mark.parametrize('data',
    [None, '', 0, 1, -1, 9999999, 'some-boom', b'\x00\xde']
)
def test_is_uuid_bad(data):
    assert utils.is_uuid(data) == False


def test_totupe():
    assert utils.totupe('0.1') == (0, 1)
    assert utils.totupe('1.0.1') == (1, 0, 1)
    assert utils.totupe('2.2-dev') == (2, 2)


def test_human_time():
    assert utils.human_time(0) == '00:00:00'
    assert utils.human_time(11) == '00:00:11'
    assert utils.human_time(3666) == '01:01:06'


def test_human_bytes():
    assert utils.human_bytes(0) == '0'
    assert utils.human_bytes(-1) == '0'
    assert utils.human_bytes(123) == '123'
    assert utils.human_bytes(12345) == '12.1KB'
    assert utils.human_bytes(12345678) == '11.8MB'
    assert utils.human_bytes(1234567890) == '1.15GB'


def test_get_koi():
    payload = {
        '1': 1,
        '2': [
            {
                '3': 3,
                '4': [4]
            }
        ]
    }
    assert utils.get_koi(payload, ['1', '3']) == {'1': 1, '3': 3}
    payload = '[{"1": 1}]'
    assert utils.get_koi(payload, ['1']) == {'1': 1}
    assert utils.get_koi({}, ['1']) == {'1': None}
    assert utils.get_koi('', ['1']) == {'1': None}
    assert utils.get_koi(0, ['1']) == {'1': None}
    assert utils.get_koi(None, ['1']) == {'1': None}


def test_hash_file():
    fmd5 = '202cb962ac59075b964b07152d234b70'
    with tempfile.NamedTemporaryFile() as tf:
        tf.write(b'123')
        tf.flush()
        tf.seek(0)
        assert utils.hash_file(tf.name) == fmd5
        assert fmd5 in open(tf.name + '.md5').read()
