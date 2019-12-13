import os
import time
import shutil
import pytest
import tempfile
from andriller import config
from andriller import __version__


@pytest.fixture
def c():
    os.environ['HOME'] = tempfile.mkdtemp()
    yield config.Config()
    shutil.rmtree(os.environ['HOME'])


def test_config_funcs(c):
    assert c.NS == 'DEFAULT'
    n = int(time.time())
    x = c.hex_time_now()
    assert type(x) == str and len(x) == 8
    assert c.time_from_hex(x) in range(n, n + 1)


@pytest.mark.parametrize('key,current,new', [
    ('version', __version__, '9.9.9'),
    ('update_rate', '100000', '2000000'),
    ('theme', '', 'clam'),
])
def test_update_records(c, key, current, new):
    assert c(key) == current
    c.update_conf(**{c.NS: {key: new}})
    assert c(key) == new
