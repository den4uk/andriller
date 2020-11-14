import sys
import pytest
import tempfile
import subprocess
from unittest import mock
from andriller import adb_conn

fake_adb = tempfile.NamedTemporaryFile()


@pytest.fixture
def ADB(mocker):
    mocker.patch('andriller.adb_conn.ADBConn.kill')
    mocker.patch('andriller.adb_conn.ADBConn._opt_use_capture', return_value=True)
    with mock.patch('andriller.adb_conn.ADBConn._get_adb_bin', return_value=fake_adb.name):
        with mock.patch('andriller.adb_conn.ADBConn._adb_has_exec', return_value=True):
            adb = adb_conn.ADBConn()
    adb_cmd = adb.adb.__func__
    setattr(adb, 'adb', lambda *args, **kwargs: adb_cmd(adb, *args, **kwargs))
    return adb


@pytest.fixture
def ADB_alt(mocker):
    mocker.patch('andriller.adb_conn.ADBConn.kill')
    mocker.patch('andriller.adb_conn.ADBConn._opt_use_capture', return_value=False)
    with mock.patch('andriller.adb_conn.ADBConn._get_adb_bin', return_value=fake_adb.name):
        with mock.patch('andriller.adb_conn.ADBConn._adb_has_exec', return_value=False):
            adb = adb_conn.ADBConn()
    adb_cmd = adb.adb.__func__
    setattr(adb, 'adb', lambda *args, **kwargs: adb_cmd(adb, *args, **kwargs))
    return adb


@pytest.fixture
def ADB_win(mocker):
    mock_sub = mocker.patch('andriller.adb_conn.subprocess', autospec=True)
    mock_sub.STARTUPINFO = mock.MagicMock()
    mock_sub.STARTF_USESHOWWINDOW = mock.MagicMock()
    mocker.patch('andriller.adb_conn.ADBConn.kill')
    mocker.patch('andriller.adb_conn.ADBConn._opt_use_capture', return_value=True)
    with mock.patch('sys.platform', return_value='win32'):
        with mock.patch('andriller.adb_conn.ADBConn._get_adb_bin', return_value=fake_adb.name):
            with mock.patch('andriller.adb_conn.ADBConn._adb_has_exec', return_value=True):
                adb = adb_conn.ADBConn()
    return adb


def test_init_windows(ADB_win):
    assert ADB_win.startupinfo is not None
    assert ADB_win.rmr == b'\r\r\n'


@pytest.mark.parametrize('file_path, result', [
    ('/some/file.txt', '/some/file.txt\n'),
    ('/some/my file.txt', '/some/my file.txt\n'),
    ('some/file.txt', 'some/file.txt\n'),
])
def test_file_regex(file_path, result):
    assert adb_conn.ADBConn._file_regex(file_path).match(result)


def test_adb_simple(ADB, mocker):
    output = mock.Mock(stdout=b'lala', returncode=0)
    mock_run = mocker.patch('andriller.adb_conn.subprocess.run', return_value=output)

    res = ADB('hello')
    assert res == 'lala'
    mock_run.assert_called_with([fake_adb.name, 'hello'],
        capture_output=True, shell=False, startupinfo=None)


def test_adb_simple_su(ADB, mocker):
    output = mock.Mock(stdout=b'lala', returncode=0)
    mock_run = mocker.patch('andriller.adb_conn.subprocess.run', return_value=output)

    res = ADB('hello', su=True)
    assert res == 'lala'
    mock_run.assert_called_with([fake_adb.name, 'su -c', 'hello'],
        capture_output=True, shell=False, startupinfo=None)


def test_adb_binary(ADB, mocker):
    output = mock.Mock(stdout=b'lala', returncode=0)
    mock_run = mocker.patch('andriller.adb_conn.subprocess.run', return_value=output)

    res = ADB('hello', binary=True)
    assert res == b'lala'
    mock_run.assert_called_with([fake_adb.name, 'hello'],
        capture_output=True, shell=False, startupinfo=None)


def test_adb_out(ADB, mocker):
    output = mock.Mock(stdout=b'uid(1000)', returncode=0)
    mock_run = mocker.patch('andriller.adb_conn.subprocess.run', return_value=output)

    res = ADB.adb_out('id', binary=False)
    assert res == 'uid(1000)'
    mock_run.assert_called_with([fake_adb.name, 'shell', 'id'],
        capture_output=True, shell=False, startupinfo=None)


def test_adb_out_alt(ADB_alt, mocker):
    output = mock.Mock(stdout=b'uid(1000)', returncode=0)
    mock_run = mocker.patch('andriller.adb_conn.subprocess.run', return_value=output)

    res = ADB_alt.adb_out('id', binary=True)
    assert res == b'uid(1000)'
    mock_run.assert_called_with([fake_adb.name, 'shell', 'id'],
        stdout=subprocess.PIPE, shell=False, startupinfo=None)


def test_adb_out_win(ADB_win, mocker):
    output = mock.Mock(stdout=b'uid(1000)\r\r\n', returncode=0)
    mock_run = mocker.patch('andriller.adb_conn.subprocess.run', return_value=output)

    res = ADB_win.adb_out('id', binary=True)
    assert res == b'uid(1000)\n'


def test_adb_out_uses_exec(ADB, mocker):
    ADB._is_adb_out_post_v5 = True
    output = mock.Mock(stdout=b'uid(1000)', returncode=0)
    mock_run = mocker.patch('andriller.adb_conn.subprocess.run', return_value=output)

    res = ADB.adb_out('id', binary=False)
    assert res == 'uid(1000)'
    mock_run.assert_called_with([fake_adb.name, 'exec-out', 'id'],
        capture_output=True, shell=False, startupinfo=None)
