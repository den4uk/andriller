import os
import re
import time
import shutil
import logging
import tarfile
import pathlib
import tempfile
import webbrowser
import threading
from contextlib import suppress
from timeout_decorator.timeout_decorator import TimeoutError
from . import utils
from . import engines
from . import messages
from . import decoders
from . import adb_conn

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
class ChainExecution:
    USER = 'shell'
    ROOT = 'root'
    ROOTSU = 'root-su'
    DATA_STORE = 'DataStore.tar'
    extract_dir = 'data'

    def __init__(self, base_dir, status_msg=None, use_adb=False, **kwargs):
        self.tools = utils.DrillerTools()
        self.base_dir = base_dir
        self.work_dir = None
        self.updater = status_msg
        if use_adb:
            self.adb = adb_conn.ADBConn()
        self.registry = decoders.Registry()
        self.targets = None
        self.REPORT = {}
        self.DECODED = []
        self.DOWNLOADS = []
        self.DataStore = None
        self.do_shared = kwargs.get('do_shared', False)
        self.backup = kwargs.get('backup')
        # self.backup_pw = kwargs.get('backup_pw')  # TODO
        self.tarfile = kwargs.get('tarfile')
        self.src_dir = kwargs.get('src_dir')
        self.WB = None
        self.logger = kwargs.get('logger', logger)

    def setup(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        data_store = os.path.join(self.work_dir, self.DATA_STORE)
        self.DataStore = tarfile.open(data_store, 'a')

    def CleanUp(self):
        self.DataStore.close()
        datastore_file = os.path.abspath(self.DataStore.fileobj.name)
        utils.hash_file(datastore_file)
        # Delete temp tar file
        default_temp = tempfile.gettempdir()
        tf = self.tarfile
        if tf and os.path.isfile(tf) and tf.startswith(default_temp):
            os.remove(tf)
        self.update('Finished.')

    def update(self, msg, info=True):
        self.logger.info(msg) if info else logger.debug(msg)
        if self.updater:
            self.updater.set(msg)
            self.updater._root.update()

    def InitialAdbRead(self):
        self.update('Reading information...')

        def get_permission():
            self.su = False
            if 'root' in self.adb('exec-out id'):
                self.permisson = self.ROOT
                return self.permisson
            try_su = self.adb('exec-out id', su=True)
            if try_su is not None and self.ROOT in try_su:
                self.permisson = self.ROOTSU
                self.su = True
            else:
                self.permisson = self.USER
            return self.permisson

        def get_prop(prop: list, key: str):
            for row in prop:
                if key in row:
                    return row.strip().split('=')[1]

        def get_wifi(dump: list):
            dump = list(filter(lambda x: x.startswith('mWifiInfo'), dump))
            if dump:
                src = re.search(r'MAC: ([:0-9a-f]{17}),', dump[0])
                if src:
                    return src.groups()[0]

        def get_accounts(dump):
            accs = re.findall(r'Account \{name=(.+?), type=(.+?)\}', dump, re.S)
            return [(v, k) for k, v in accs]

        # Serial, status, permissions
        self.REPORT['serial'], self.REPORT['status'] = self.adb.device()
        self.REPORT['permisson'] = get_permission()

        # Build Props
        with suppress(TimeoutError):
            build_prop = self.adb('exec-out cat /system/build.prop', su=self.su, timeout=5)
            if build_prop:
                build_prop = build_prop.split('\n')
                props = [
                    'ro.product.manufacturer',
                    'ro.product.model',
                    'ro.build.version.release',
                    'ro.build.display.id']
                for p in props:
                    self.REPORT[p] = get_prop(build_prop, p)

        # WIFI
        with suppress(TimeoutError):
            _wifi = self.adb('exec-out dumpsys wifi', timeout=5)
            if _wifi:
                self.REPORT['wifi mac'] = get_wifi(_wifi.split('\n'))

        # IMEI
        with suppress(TimeoutError):
            _usbinfo = self.adb('exec-out dumpsys iphonesubinfo', timeout=5)
            if _usbinfo:
                self.REPORT['imei'] = get_prop(_usbinfo.split('\n'), 'Device ID')

        # IMEI for Android v6+
        # with suppress(TimeoutError):
        #     rex = re.compile(b' ([0-9a-f]{8})')
        #     _data = self.adb('adb shell service call iphonesubinfo 1', timeout=2)
        #     if _data and len(_data) > 9:
        #         plen = int(b''.join(_data[:2]), 16)

        # Time
        with suppress(TimeoutError):
            self.REPORT['local_time'] = time.strftime('%Y-%m-%d %H:%M:%S %Z')
            rtime = self.adb(['shell', 'date', r'+%F\ %T\ %Z'], timeout=5)
            # breakpoint()
            self.REPORT['device_time'] = rtime.split(self.adb.rmr.decode())[-1]

        # SIM Card
        with suppress(TimeoutError, Exception):
            if self.adb.exists('/data/system/SimCard.dat'):
                _simdat = self.adb('exec-out cat /data/system/SimCard.dat', su=self.su, timeout=5)
                sims = [
                    'CurrentSimSerialNumber',
                    'CurrentSimPhoneNumber',
                    'CurrentSimOperatorName',
                    'PreviousSimSerialNumber',
                    'PreviousSimPhoneNumber']
                if _simdat:
                    _simdat = _simdat.split('\n')
                    for s in sims:
                        self.REPORT[s] = get_prop(_simdat, s)

        # Accounts
        with suppress(TimeoutError):
            _acc = self.adb('exec-out dumpsys account', timeout=5)
            self.REPORT['accounts'] = get_accounts(_acc)

    @staticmethod
    def clean_name(value):
        return re.sub(r'[\s\/:*?"<>|]', '', value)

    def CreateWorkDir(self):
        date_ = time.strftime('%Y-%m-%d')
        time_ = time.strftime('%H.%M.%S')
        try:
            self.work_dir = os.path.join(
                self.base_dir,
                '{}_{}_{}_{}'.format(
                    self.clean_name(
                        self.REPORT.get('ro.product.manufacturer', self.REPORT['serial'])),
                    self.clean_name(
                        self.REPORT.get('ro.product.model', self.REPORT['permisson'])),
                    date_, time_,))
        except Exception:
            self.work_dir = os.path.join(self.base_dir, f'andriller_extraction_{date_}_{time_}')
        self.output_dir = os.path.join(self.base_dir, self.work_dir, self.extract_dir)
        self.logger.debug(f'work_dir:{self.work_dir}')
        self.logger.debug(f'output_dir:{self.output_dir}')
        self.setup()

    def download_file(self, file_path):
        """
        Return values:
        True = file downloaded
        False = file does not exist, or failed to get in full size
        None = file exists but has no size
        """
        file_remote = self.adb.exists(file_path, su=self.su)
        if file_remote:
            file_name = os.path.basename(file_remote)
            file_local = os.path.join(self.output_dir, file_name)
            remote_size = self.adb.get_size(file_path, su=self.su)
            file_saveas = os.path.join(
                os.path.split(file_local)[0],
                os.path.split(file_remote)[1])
            if remote_size == 0:
                return None
            self.logger.info(f'{file_remote} ({remote_size} bytes)')
            if self.permisson == self.ROOT:
                self.adb.pull_file(file_path, file_local)
                if os.path.exists(file_local):
                    self.DataStore.add(file_saveas, file_remote)
                    self.DOWNLOADS.append(file_name)
                    return True
            elif self.permisson == self.ROOTSU:
                for _ in range(100):
                    file_obj = self.adb.get_file(file_path, su=self.su)
                    if file_obj:
                        # remote_size = remote_size if remote_size else len(file_obj)
                        if len(file_obj) == remote_size:
                            with open(file_saveas, 'wb') as W:
                                W.write(file_obj)
                            self.DataStore.add(file_saveas, file_remote)
                            self.DOWNLOADS.append(file_name)
                            return True
                        time.sleep(0.25)
                        self.logger.debug(f'Trying again for {file_name} ({len(file_obj)} bytes)')
                else:
                    self.logger.warning(f'Failed getting file: {file_name}')
        return False

    def do_backup(self, ALL=True, shared=False, backup_name='backup.ab'):
        backup_file = os.path.join(self.work_dir, backup_name)
        cmd = [
            'backup',
            '-shared' if shared else '',
            '-all' if ALL else '',
            '-f',
            backup_file,
        ]
        com = threading.Thread(target=lambda: self.adb(cmd))
        com.start()
        if self.updater:
            messages.msg_do_backup()
        while com.is_alive():
            time.sleep(0.5)
            if os.path.exists(backup_file):
                _size = os.path.getsize(backup_file)
                self.update(f'Reading backup: {utils.human_bytes(_size)}', info=False)
        self.backup = backup_file

    def AndroidBackupToTar(self):
        self.update('Unpacking backup...')
        self.tarfile = self.tools.ab_to_tar(self.backup)

    def ExtractFromTar(self, targets=[]):
        self.update('Extracting from backup...')
        for fn in self.tools.extract_form_tar(
                self.tarfile,
                self.output_dir,
                targets=targets):
            self.DataStore.add(os.path.join(self.output_dir, fn), fn)
            self.DOWNLOADS.append(fn)

    def get_targets(self):
        self.targets = [*map(pathlib.PurePath, self.registry.get_posix_links)]

    def in_targets(self, target):
        if not self.targets:
            self.get_targets()
        target = pathlib.PureWindowsPath(target).as_posix()
        for f in self.targets:
            if f.match(target):
                return True
        return False

    @staticmethod
    def extract_form_dir(src_dir):
        src_dir_path = pathlib.Path(src_dir)
        for fobj in src_dir_path.rglob('**/*'):
            if fobj.is_file():
                yield fobj

    def ExtractFromDir(self):
        self.update('Extracting from directory...')
        src_dir_path = pathlib.Path(self.src_dir)
        for fobj in self.extract_form_dir(self.src_dir):
            fn = fobj.relative_to(src_dir_path)
            if self.in_targets(fn.name):
                self.logger.info(fn.name)
                shutil.copy2(fobj, os.path.join(self.output_dir, fn.name))
                self.DOWNLOADS.append(os.path.basename(fn))

    def enumerate_files(self, target_dir='/'):
        FILES = []
        for f in self.adb_iter(f'find {target_dir} -type f -readable'):
            FILES.append(f)

    def DataAcquisition(self, run_backup=False, shared=False):
        self.update('Acquiring data...')
        if not run_backup and self.ROOT in self.permisson:
            if shared:
                self.update('Acquiring shared storage...')
                self.do_backup(ALL=False, shared=True, backup_name='shared.ab')
            self.update('Acquiring databases via root...')
            for file_path in self.registry.get_root_links:
                self.download_file(file_path)
        elif run_backup or self.permisson == self.USER:
            self.do_backup(shared=shared)
            if self.backup and os.path.getsize(self.backup) <= 2 ** 10:
                self.logger.error('Android backup failed - too small.')
                self.backup = False

    def DataExtraction(self):
        self.update('Extracting data from source...')
        if self.backup:
            self.AndroidBackupToTar()
        if self.tarfile:
            targets = self.registry.get_all_links
            # Perhaps change to posix links?
            self.ExtractFromTar(targets=targets)
        # if self.DataStore and self.DataStore.members:
        #     pass  # TODO!

    def DecodeShared(self):
        try:
            if self.backup or (self.do_shared and self.backup):
                self.update('Decoding shared filesystem...')
                deco = decoders.SharedFilesystemDecoder(self.work_dir, self.backup)
                self.DECODED.append([deco.report_html(), f'{deco.title} ({len(deco.DATA)})'])
        except Exception as err:
            logger.exception(f'Shared decoder error: {err}')

    def DataDecoding(self):
        self.update('Decoding extracted data...')
        self.logger.debug(self.DOWNLOADS)
        workbook = self.get_master_workbook()
        for file_name in filter(None.__ne__, self.DOWNLOADS):
            if self.registry.has_target(file_name):
                for deco_class in self.registry.decoders_target(file_name):
                    file_path = os.path.join(self.output_dir, file_name)
                    try:
                        self.logger.info(f'Decoding {file_name} using {deco_class.__name__}')
                        deco = deco_class(self.work_dir, file_path)
                        if not deco.template_name:
                            continue
                        self.DECODED.append([deco.report_html(), f'{deco.title} ({len(deco.DATA)})'])
                        deco.report_xlsx(workbook=workbook)
                    except Exception as e:
                        logger.error(f'Decoding error for `{os.path.basename(file_name)}`: {e}')
                        logger.exception(str(e))

    def GenerateHtmlReport(self, open_html=True):
        self.update('Generating HTML report...')
        env = engines.get_engine()
        template_name = 'REPORT.html'
        template = env.get_template(template_name)
        report_file = os.path.join(self.work_dir, template_name)
        with open(report_file, 'w') as W:
            W.write(template.render(
                report=self.REPORT.items(),
                decoded=self.DECODED,
                **engines.get_head_foot()))
        if open_html:
            report_uri = pathlib.Path(report_file).as_uri()
            webbrowser.open_new_tab(report_uri)

    def get_master_workbook(self):
        self.WB = engines.Workbook(self.work_dir, 'REPORT')
        self.summary_sheet = self.WB.add_sheet('Summary')
        self.WB.write_header(self.summary_sheet, ['Extraction Summary'])
        return self.WB

    def GenerateXlsxReport(self):
        self.update('Generating XLSX report...')
        for row, summary in enumerate(self.DECODED, start=1):
            self.summary_sheet.write_row(row, 0, summary[1:])
        self.WB.close()


# -----------------------------------------------------------------------------
class DecodingError(Exception):
    pass
