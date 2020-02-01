import re
import sys
import shlex
import os.path
import logging
import subprocess
if sys.platform == 'win32':
    from .utils import placebo as timeout
else:
    from timeout_decorator import timeout
from .config import CODEPATH  # noqa

logger = logging.getLogger(__name__)


class ADBConn:
    """
    Class for all adb (android debugging bridge communications).
    For Windows, binary files are supplied.
    For Mac/Linux, install binaries via brew/apt/pacman.
    """
    UNIX = ['linux', 'linux2', 'darwin']
    MODES = {
        'download': 'download',
        'bootloader': 'bootloader',
        'recovery': 'recovery',
        'sideload': 'sideload',
        'sideload-auto-reboot': 'sideload-auto-reboot',
    }

    def __init__(self, logger=logger, log_level=logging.INFO):
        """
        logger: optional, pass a dedicated loggger instance, else default will be used.
        log_level: optional, logging level.
        """
        self.startupinfo = None
        self.adb_bin = None
        self.platform = sys.platform
        self.rmr = b'\r\n'
        self.setup(log_level)

    def setup(self, log_level):
        self.logger = logger
        self.logger.setLevel(log_level)
        self.logger.debug(f'Platform: {self.platform}')
        if self.platform in self.UNIX:
            self.adb_bin = self.cmd_shell('which adb') or None
            self.logger.debug(f'Using adb binary `{self.adb_bin}`')
        else:
            self.adb_bin = os.path.join(CODEPATH, 'bin', 'adb.exe')
            self._win_startupinfo()
        if not self.adb_bin or not os.path.exists(self.adb_bin):
            self.logger.warning('ADB binary is not found!')
            raise ADBConnError('ADB binary is not found!')

    def _win_startupinfo(self):
        self.startupinfo = subprocess.STARTUPINFO()
        self.startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.rmr = b'\r\r\n'

    @property
    def run_opt(self):
        opt = {'shell': False, 'startupinfo': self.startupinfo}
        if tuple(sys.version_info) >= (3, 7):
            opt['capture_output'] = True
        else:
            opt['stdout'] = subprocess.PIPE
        return opt

    @timeout(60 * 60 * 2, use_signals=False)
    def adb(self, cmd, binary=False, su=False, **kwargs) -> str:
        """
        Runs an adb command and returns the output as a string.

        Args:
            cmd (str): adb command.
            binary (bool): returns bytes output instead of str.
            su (bool): use superuser if the target device has it.

        Example:
            to run `adb shell id` do: self.adb('shell id')
        """
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if su:
            cmd.insert(1, 'su -c')
        self.logger.debug(f'ADB: {cmd}')
        run = subprocess.run([self.adb_bin] + cmd, **self.run_opt)
        if run.stdout and run.returncode == 0:
            if binary:
                return run.stdout
            return run.stdout.decode().strip()

    def cmditer(self, cmd):
        process = subprocess.Popen(
            shlex.split(cmd),
            shell=False,
            startupinfo=self.startupinfo,
            stdout=subprocess.PIPE)
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                yield output.decode().rstrip()
        rc = process.poll()
        return rc

    def device(self):
        dev = self.adb('devices', timeout=5)
        if dev:
            dev = dev.split('\n')
            if len(dev) > 1:
                dev = dev[1].split('\t')
                return dev
        else:
            self.logger.error('ADB binary cannot be used to check for connected devices!')
        return [None, None]

    def start(self):
        self.adb('start-server', timeout=10)

    def kill(self):
        self.adb('kill-server', timeout=5)

    @staticmethod
    def _file_regex(fp):
        return re.compile(f"^{fp.replace('*', '(.+?)')}$")

    def exists(self, file_path, **kwargs):
        file_path_strict = self.strict_name(file_path)
        file_remote = self.adb(f'shell ls {file_path_strict}', **kwargs)
        if not file_remote:
            return None
        if re.match(self._file_regex(file_path), file_remote):
            return file_remote

    def get_file(self, file_path, **kwargs) -> bytes:
        """
        Returns binary content of a file.

        Args:
            file_path (str|Path): Remote file path.
        """
        file_path_strict = self.strict_name(file_path)
        data = self.adb(f'exec-out cat {file_path_strict}', binary=True, **kwargs)
        return data

    def pull_file(self, file_path, dst_path, **kwargs):
        """
        Uses pull command to copy a file.

        Args:
            file_path (str|Path): Remote file path.
            dst_path (str|Path): Local file path where to save.
        """
        file_path_strict = re.sub(' ', r'\ ', file_path)
        dst_path_strict = re.sub(' ', r'\ ', dst_path)
        self.adb(f"pull {file_path_strict} {dst_path_strict}")

    def get_size(self, file_path, **kwargs) -> int:
        """
        Returns remote file size in bytes.

        Args:
            file_path (str|Path): Remote file path.
        """
        file_path_strict = self.strict_name(file_path)
        size = self.adb(f'shell stat -c %s {file_path_strict}', **kwargs)
        if not size.isdigit():
            size = self.adb(f'shell ls -nl {file_path_strict}', **kwargs).split()[3]
            if not size.isdigit():
                size = self.adb(f'shell wc -c < {file_path_strict}', **kwargs)
                if not size.isdigit():
                    self.logger.debug(f'Size Error: {size}')
                    return -1
        return int(size)

    @timeout(30, use_signals=False)
    def cmd_shell(self, cmd, code=False, **kwargs):
        self.logger.debug(f'CMD: {cmd}')
        run = subprocess.run(shlex.split(cmd), **self.run_opt)
        if code:
            return run.returncode
        else:
            if run.stdout:
                return run.stdout.decode().strip()

    def reboot(self, mode=None):
        mode = self.MODES.get(mode, '')
        self.logger.info(f'Rebooting in {mode}.')
        self.adb(f"reboot {mode}", timeout=20)

    def __call__(self, cmd, *args, **kwargs):
        return self.adb(cmd, *args, **kwargs)

    @staticmethod
    def strict_name(file_path):
        file_name = os.path.split(file_path)[1]
        if ' ' in file_name:
            return file_path.replace(file_name, repr(file_name).replace(' ', r'\ '))
        return file_path


class ADBConnError(Exception):
    pass
