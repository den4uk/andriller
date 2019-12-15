import os
import re
import abc
import base64
import logging
import pathlib
import sqlite3
import datetime
import xml.etree.ElementTree
from contextlib import suppress
from . import config
from . import engines

logger = logging.getLogger(__name__)

SQLITE_MAGIC = b'SQLite format 3\x00'


class AndroidDecoder:
    """
    Main decoder class for Android databases. It's subclasses are also used in the Registry.
    TARGET (str): database name, eg: 'my_database.db'
    RETARGET (str): a regex-like string, where the database name is not static, eg: 'store_91237635238734535.db'
    NAMESPACE (str): package namespace options are: db|r|f|sp; 'db' is for 'databases', 'sp' is for 'shared_preferences', etc.
    PACKAGE (str): package name for the application, eg: 'my_app.example.com'
    EXTRAS (List[str]): extra support files needed for decoding.
    """
    TARGET = None
    RETARGET = None
    NAMESPACE = None  # db|r|f|sp
    PACKAGE = None
    EXTRAS = []
    exclude_from_menus = False
    exclude_from_registry = False
    exclude_from_decoding = False  # For ambitious target names (eg: '*.db')

    def __init__(self, work_dir, input_file, stage=False, **kwargs):
        """
        Contructor options:
        work_dir (str|Path): directory where to output reports.
        input_file (str|Path): input file (as intended self.TARGET) locally on the system.
        stage (bool): if True, the decoder will initialise but won't run decoding.
        """
        self.work_dir = work_dir
        self.input_file = input_file
        self.title = None
        self.Titles = {}  # {<key for XLSX>: <Title name for HTML>}
        self.template_name = None  # HTML template
        self.logger = kwargs.get('logger', logger)
        if not stage:
            self.logger.debug(f'decoder:{type(self).__name__}')
            self.logger.debug(f'work_dir:{work_dir}')
            self.logger.debug(f'input_file:{input_file}')
            self.DATA = []  # main storage for decoded data
            self.main()

    @property
    def conf(self):
        if not hasattr(self, '_conf'):
            self._conf = config.Config()
        return self._conf

    @abc.abstractclassmethod
    def main(self):
        # Make the magic happen here
        # populate `self.DATA` list with decoded objects
        pass

    @property
    def target_path_ab(self):
        return self.gen_target_path(self, is_ab=True)

    @property
    def target_path_root(self):
        return self.gen_target_path(self)

    @property
    def target_path_posix(self):
        return self.gen_target_path(self, is_posix=True)

    @staticmethod
    def gen_target_path(cls, is_posix=False, is_ab=False):
        if all([cls.PACKAGE, cls.NAMESPACE, cls.TARGET]):
            BASE = '' if is_posix else 'apps/' if is_ab else '/data/data/'
            NS = '*' if is_posix else cls.NAMESPACE if is_ab else cls.get_namespace(cls.NAMESPACE)
            return f'{BASE}{cls.PACKAGE}/{NS}/{cls.RETARGET or cls.TARGET}'

    @staticmethod
    def get_namespace(name):
        return {
            'db': 'databases',
            'f': 'files',
            'r': 'resources',
            'sp': 'shared_prefs',
        }.get(name, name)

    def get_artifact(self, path_property):
        # Pass path property, such as `self.root_path` or `self.ab_path`
        SQLITE_SUFFIXES = ['', '-shm', '-wal', '-journal']
        if self.NAMESPACE == 'db' or getattr(self, 'target_is_db', False):
            return [f'{path_property}{suf}' for suf in SQLITE_SUFFIXES]
        return [path_property]

    def get_neighbour(self, neighbour, **kwargs):
        input_dir = os.path.dirname(self.input_file)
        if neighbour in os.listdir(input_dir):
            neighbour = os.path.join(input_dir, neighbour)
            if os.path.isfile(neighbour):
                return neighbour
        return False

    @classmethod
    def add_extra(cls, namespace, target):
        class Extra(cls):
            TARGET = target
            NAMESPACE = namespace
            PACKAGE = cls.PACKAGE
        cls.EXTRAS.append(Extra)

    def get_extras(self, **kwargs):
        return [self.gen_target_path(xtr, **kwargs) for xtr in self.EXTRAS]

    @staticmethod
    def name_val(d, key='name', value='value'):
        return {d[key]: d[value]}

    @classmethod
    def staged(cls):
        return cls(None, None, stage=True)

# -----------------------------------------------------------------------------
    def check_sqlite_magic(self):
        if os.path.isfile(self.input_file):
            with open(self.input_file, 'rb') as R:
                if R.read(len(SQLITE_MAGIC)) == SQLITE_MAGIC:
                    return True
        msg = f'Target file `{os.path.basename(self.input_file)}` is not an SQLite database or it is encrypted!'
        self.logger.error(msg)
        raise DecoderError(msg)

    @property
    def sqlite_readonly(self):
        self.check_sqlite_magic()
        input_file = pathlib.PurePath(os.path.abspath(self.input_file))
        return f'{input_file.as_uri()}?mode=ro'

    def zipper(self, keys, values):
        return {k: v for (k, v) in zip(keys, values)}

    def get_sql_tables(self):
        with sqlite3.connect(self.sqlite_readonly, uri=True) as conn:
            c = conn.cursor()
            return tuple(x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'"))

    def get_table_columns(self, table_name):
        with sqlite3.connect(self.sqlite_readonly, uri=True) as conn:
            c = conn.cursor()
            return tuple(x[1] for x in c.execute(f"PRAGMA table_info({table_name})"))

    def sql_table_as_dict(self, table, columns='*', order_by=None, order="DESC", where={}):
        with sqlite3.connect(self.sqlite_readonly, uri=True) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            # table_names = tuple(x[1] for x in c.execute(f"PRAGMA table_info({table})"))
            # if (order_by is not None) and (order_by not in table_names):
            #     raise NameError(f"Column `{order_by}` is not in `{table}` table")
            query = f"SELECT {','.join(columns)} FROM {table}"
            if where:
                query += f' WHERE {self.where(where)}'
            if order_by:
                query += f" ORDER BY {order_by} {order}"
            self.logger.debug(f"SQL> {query}")
            return (self.zipper(row.keys(), row) for row in c.execute(query))

    def sql_table_rows(self, table, columns='*', where={}):
        with sqlite3.connect(self.sqlite_readonly, uri=True) as conn:
            c = conn.cursor()
            query = f"SELECT {','.join(columns)} FROM {table}"
            if where:
                query += f' WHERE {self.where(where)}'
            self.logger.debug(f"SQL> {query}")
            return c.execute(query)

    @staticmethod
    def where(params: dict):
        where_all = []
        keyval = lambda k, v: f"{k}='{v}'"  # noqa: E731
        for key, vals in params.items():
            sep = 'OR'
            if key.startswith('!'):
                key = key.replace('!', 'NOT ')
                sep = 'AND'
            if isinstance(vals, (list, set, tuple)):
                group = f' {sep} '.join([keyval(key, v) for v in vals])
                where_all.append(f'({group})')
            else:
                where_all.append(keyval(key, vals))
        return ' AND '.join(where_all)

    def get_head_foot(self):
        return {
            'header': self.conf('custom_header'),
            'footer': self.conf('custom_footer'),
        }

    def report_html(self):
        env = engines.get_engine()
        template = env.get_template(self.template_name)
        report_file = os.path.join(self.work_dir, f'{self.title}.html')
        with open(report_file, 'w', encoding='UTF-8') as W:
            W.write(template.render(
                DATA=self.DATA,
                title=self.title,
                Titles=self.Titles.values(),
                **self.get_head_foot()))
        return os.path.relpath(report_file, self.work_dir)

    def report_xlsx(self, workbook=None, to_close=False):
        if not workbook:
            to_close = True
            workbook = engines.Workbook(self.work_dir, self.title)
        sheet = workbook.add_sheet(self.title)
        col_vals, col_names = zip(*self.Titles.items())
        workbook.write_header(sheet, col_names)
        for row, data in enumerate(self.DATA, start=1):
            data['_id'] = data.get('_id', row)
            row_vals = (data.get(k) for k in col_vals)
            sheet.write_row(row, 0, row_vals)
        if to_close:
            workbook.close()
            return os.path.relpath(workbook.file_path, self.work_dir)

    @staticmethod
    def duration(value):
        return f'{str(datetime.timedelta(seconds=value)):0>8}'

    def unix_to_time(self, unix_stamp: int) -> str:
        if int(unix_stamp) > 0:
            d = datetime.datetime.fromtimestamp(int(unix_stamp), self.conf.tzone)
            return d.strftime(self.conf.date_format)

    def unix_to_time_ms(self, unix_stamp: int) -> str:
        if int(unix_stamp) > 0:
            d = datetime.datetime.fromtimestamp(int(unix_stamp) // 1000, self.conf.tzone)
            return d.strftime(self.conf.date_format)

    def webkit_to_time(self, webkit_stamp: int) -> str:
        if int(webkit_stamp) > 0:
            epoch = datetime.datetime(1601, 1, 1, tzinfo=self.conf.tzone)
            d = datetime.timedelta(microseconds=int(webkit_stamp))
            return (epoch + d).strftime(self.conf.date_format)

    @staticmethod
    def to_chars(data) -> str:
        if not data:
            return ''
        if isinstance(data, str):
            data = data.encode()
        return ''.join(map(chr, data))

    @classmethod
    def safe_str(cls, value):
        if isinstance(value, (str, float, int)):
            return value
        with suppress(AttributeError, UnicodeDecodeError):
            return value.decode()
        return cls.to_chars(value)

    @staticmethod
    def b64e(data: bytes) -> str:
        return base64.b64encode(data).decode()

    @staticmethod
    def call_type(value):
        call_types = {
            1: 'Received',
            2: 'Dialled',
            3: 'Missed',
            4: 'Voicemail',
            5: 'Rejected',
            6: 'Blocked',
        }
        return call_types.get(value, f'Unknown({value})')

    @staticmethod
    def sms_type(value):
        sms_types = {
            1: 'Inbox',
            2: 'Sent',
            3: 'Draft',
            # 4: '',  # Outgoing?
            5: 'Sending failed',
            6: 'Sent',
        }
        return sms_types.get(value, f'Unknown({value})')

    @staticmethod
    def skype_msg_type(value):
        msg_types = {
            1: 'Unsent',
            2: 'Sent',
            3: 'Unread',
            4: 'Read'
        }
        return msg_types.get(value, f'Unknown({value})')

    @staticmethod
    def skype_call_type(value):
        return {
            5: 'Incoming',
            6: 'Outgoing',
        }.get(value, f'Unknown({value})')

    @staticmethod
    def http_status(status):
        return {
            190: 'Pending',
            192: 'Running',
            193: 'Paused',
            200: 'Success',
            301: 'Redirected',
            302: 'Found',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Not Permitted',
            404: 'Not Found',
            406: 'Not Acceptable',
            488: 'Already Exists',
            489: 'Cannot Resume',
            490: 'Cancelled',
            500: 'Server Error',
            502: 'Bad Gateway',
            503: 'Unavailable',
            504: 'Gateway Timeout',
        }.get(status, f'Code({status})')

    @staticmethod
    def parse_number(value):
        if not value:
            return ''
        value = re.sub(r'(?<=\d)\s(?=\d)', '', str(value))
        num_types = {'-2': 'WITHHELD', '-1': 'UNKNOWN'}
        return num_types.get(value, value)

    @staticmethod
    def xml_root(file_path):
        tree = xml.etree.ElementTree.parse(file_path)
        return tree.getroot()

    @classmethod
    def xml_get_tag_text(cls, file_path, tag, attr, value):
        root = cls.xml_root(file_path)
        for t in root.findall(tag):
            attrib = t.attrib
            if attr in attrib and value in attrib.values():
                return t.text


# -----------------------------------------------------------------------------
class DecoderError(Exception):
    pass
