import pytest
import tempfile
from unittest import mock
from andriller import adb_conn


fake_adb = tempfile.NamedTemporaryFile()


@pytest.fixture
def ADB():
    with mock.patch('andriller.adb_conn.ADBConn.cmd_shell', return_value=fake_adb.name):
        adb = adb_conn.ADBConn()
    return adb


@pytest.fixture
def ADB_win():
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
