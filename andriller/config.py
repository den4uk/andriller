import os
import sys
import time
import logging
import pathlib
import datetime
import requests
import configparser
from contextlib import suppress
from appdirs import AppDirs
from . import utils
from . import statics
from . import __version__, __package_name__

logger = logging.getLogger(__name__)

TIME_ZONES = {
    datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=h))
    ).strftime("%Z"): h for h in range(-12, 15)
}

CODEPATH = pathlib.Path(__file__).absolute().parents[1] if \
    hasattr(sys, 'frozen') else pathlib.Path(__file__).absolute().parent


class Config:
    NS = 'DEFAULT'

    def __init__(self):
        self.OS = sys.platform
        self.appdirs = AppDirs(appname=__package_name__)
        self.config_file = os.path.join(self.appdirs.user_config_dir, 'config.ini')
        self.conf = configparser.ConfigParser(allow_no_value=True)
        self.make_folders_files()
        self.tzone = None
        self.date_format = None
        self.setup_tz()
        self.update_available = False

    def __call__(self, key):
        return self.conf[self.NS][key]

    def setup_tz(self):
        tzo = TIME_ZONES.get(self('time_zone'), 0)
        self.tzone = datetime.timezone(datetime.timedelta(hours=tzo))
        self.date_format = ''.join(map(lambda x: f'%{x}' if x.isalpha() else x, self('date_format')))

    def make_folders_files(self):
        if not os.path.exists(self.appdirs.user_config_dir):
            os.makedirs(self.appdirs.user_config_dir)
        if not os.path.isfile(self.config_file):
            self.initialise()
        self.conf.read(self.config_file)
        if utils.totupe(__version__) > utils.totupe(self.conf[self.NS]['version']):
            self.conf[self.NS]['version'] = __version__
            conf_data = self.default_user_config()
            for k, v in conf_data[self.NS].items():
                if k not in self.conf[self.NS]:
                    self.conf[self.NS][k] = str(v)
            self.update_conf()

    def initialise(self):
        base = self.default_user_config()
        self.update_conf(**base)

    def update_conf(self, **DATA):
        for namespace in DATA:
            for key, value in DATA[namespace].items():
                self.conf[namespace][key] = str(value)
        with open(self.config_file, 'w+') as cfw:
            self.conf.write(cfw)
        self.conf.read(self.config_file)
        self.setup_tz()

    @staticmethod
    def hex_time_now() -> str:
        now = int(time.time())
        return hex(now)[2:]

    @staticmethod
    def time_from_hex(val: str) -> int:
        return int(val, 16)

    @classmethod
    def default_user_config(cls):
        return {
            cls.NS: {
                'version': __version__,
                'default_path': os.path.expanduser('~'),
                'last_path': os.path.expanduser('~'),
                'dict_path': os.path.expanduser('~'),
                'update_rate': 100000,
                'offline_mode': 0,
                'window_size': 20,
                'save_log': 1,
                'theme': '',
                'date_format': 'Y-m-d H:M:S Z',
                'time_zone': 'UTC',
                'custom_header': statics.DEFAULT_HEADER,
                'custom_footer': statics.DEFAULT_FOOTER,
            },
        }

    @property
    def is_mac(self):
        return self.OS == 'darwin'

    @utils.threaded
    def check_latest_version(self, logger=logger):
        url = f'https://pypi.org/pypi/{__package_name__}/json'
        with suppress(Exception):
            response = requests.get(url)
            if response.ok and response.headers.get('Content-Type') == 'application/json':
                latest = max(response.json()['releases'])
                logger.debug(f'Fetched latest version from PYPI: {latest}')
                if utils.totupe(__version__) < utils.totupe(latest):
                    logger.warning(f'  ** Update available: {latest} **')
                    self.update_available = True

    @utils.threaded
    def upgrade_package(self, package=__package_name__, logger=logger):
        from .adb_conn import ADBConn
        cmd = f'{sys.executable} -m pip install {package} -U'
        for line in ADBConn.cmditer(cmd):
            logger.info(line)
