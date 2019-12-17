import os
import json
import time
import shutil
import pytest
import tempfile
import requests
from unittest import mock
from andriller import config
from andriller import __version__


@pytest.fixture
def conf():
    os.environ['HOME'] = tempfile.mkdtemp()
    yield config.Config()
    shutil.rmtree(os.environ['HOME'])


def test_config_funcs(conf):
    assert conf.NS == 'DEFAULT'
    n = int(time.time())
    x = conf.hex_time_now()
    assert type(x) == str and len(x) == 8
    assert conf.time_from_hex(x) in range(n, n + 1)


@pytest.mark.parametrize('key,current,new', [
    ('version', __version__, '9.9.9'),
    ('update_rate', '100000', '2000000'),
    ('theme', '', 'clam'),
])
def test_update_records(conf, key, current, new):
    assert conf(key) == current
    conf.update_conf(**{conf.NS: {key: new}})
    assert conf(key) == new


@pytest.mark.parametrize('version, result', [
    ('9.8.7', True),
    ('1.2.3', False),
])
def test_check_latest_version(conf, version, result):
    response_obj = requests.Response()
    response_obj.status_code = 200
    response_obj.headers['Content-Type'] = 'application/json'
    response_obj._content = json.dumps({'releases': {version: ''}}).encode()

    with mock.patch('andriller.config.requests.get', return_value=response_obj):
        conf.check_latest_version()
        assert conf.update_available == result
