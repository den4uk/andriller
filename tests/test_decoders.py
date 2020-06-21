import os
import pytest
import tempfile
from andriller import decoders


@pytest.fixture(autouse=True)
def make_home():
    with tempfile.TemporaryDirectory() as fake_home:
        os.environ['HOME'] = fake_home
        yield


def test_calls_one():
    base_dir = tempfile.TemporaryDirectory()
    src_file = os.path.join(os.path.dirname(__file__),
        'data', 'data', 'com.android.providers.contacts', 'db', 'calllog.db')

    deco = decoders.AndroidOneCallsDecoder(base_dir, src_file)
    assert isinstance(deco.DATA, list)
    assert len(deco.DATA) > 0

    i = deco.DATA[0]
    assert isinstance(i, dict)
    assert i['type'] == 'Dialled'
    assert i['number'] == '+441234567890'
    assert i['date'].startswith('2020-05-07')
