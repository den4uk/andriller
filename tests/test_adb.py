import pytest
import tempfile
from unittest import mock
# from pytest_mock import mocker
from andriller import adb_conn

fake_adb = tempfile.NamedTemporaryFile()


@pytest.fixture
def ADB(mocker):
    mocker.patch('andriller.adb_conn.ADBConn.kill')
    with mock.patch('andriller.adb_conn.ADBConn.cmd_shell', return_value=fake_adb.name):
        adb = adb_conn.ADBConn()
    adb_cmd = adb.adb.__func__.__wrapped__
    setattr(adb, 'adb', lambda *args, **kwargs: adb_cmd(adb, *args, **kwargs))
    return adb


@pytest.fixture
def ADB_win(mocker):
    mocker.patch('andriller.adb_conn.ADBConn.kill')
    with mock.patch('sys.platform', return_value='win32'):
        adb = adb_conn.ADBConn()
    return adb


@mock.Mock('subprocess.STARTUPINFO')
def test_init_windows(ADB_win):
    assert ADB_win.startupinfo is not None


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
