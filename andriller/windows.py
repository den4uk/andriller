#!/usr/bin/env python3

import sys
import json
import glob
import struct
import string
import shutil
import os.path
import pathlib
import logging
import binascii
import datetime
import functools
import itertools
import contextlib
import webbrowser
import tkinter as tk
from tkinter import ttk, font, filedialog, messagebox
from . import __version__, __app_name__
from . import config
from . import driller
from . import statics
from . import adb_conn
from . import decrypts
from . import decoders
from . import messages
from . import cracking
from . import screencap
from .utils import threaded, human_bytes, DrillerTools
from .tooltips import createToolTip

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def disable_control(event, *args, **kwargs):
    try:
        event.widget.config(state=tk.DISABLED)
        yield
    finally:
        event.widget.config(state=tk.NORMAL)


class TextFieldHandler(logging.Handler):
    def __init__(self, tk_obj, level=logging.NOTSET):
        super().__init__(level=level)
        self.tk_obj = tk_obj

    def emit(self, record):
        try:
            log = self.format(record)
            self.tk_obj.insert('end', f'{log}\n')
            self.tk_obj.see('end')
        except Exception:
            self.handleError(record)


def log_errors(method):
    @functools.wraps(method)
    def func(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as e:
            self.logger.exception(f'{e}')
    return func


class BaseWindow:
    def __init__(self, root=None, title=__app_name__, **kwargs):
        self.log_level = kwargs.get('log_level', logging.INFO)
        logger.setLevel(self.log_level)
        if root:
            self.root = tk.Toplevel(root, takefocus=True)
            self.root.protocol("WM_TAKE_FOCUS")
            self.root.transient(root)
            self.root.bind('<Escape>', lambda e: self.root.destroy())
        else:
            self.root = tk.Tk()
            self.root.bind('<Double-Escape>', self.quit_app)
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.title(title)
        self.root.resizable(False, False)
        self.set_icon()
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.NWES = (tk.N, tk.W, tk.E, tk.S)
        self.WE = (tk.W, tk.E)
        logo_ = os.path.join(config.CODEPATH, 'res', 'logo.gif')
        self.img_logo = tk.PhotoImage(master=root, file=logo_)
        self.style_ttk = ttk.Style()
        self.conf = config.Config()
        if self.conf('theme'):
            self.style_ttk.theme_use(self.conf('theme'))

        self.FontMono = self.get_monospace_font()
        self.FontStatus = font.Font(size='10', weight='bold')
        self.FontTitle = font.Font(size='12', weight='bold')
        self.FontInfo = font.Font(size='9', slant='italic')

        self.OUTPUT = tk.StringVar()

        self.mainframe = ttk.Frame(self.root, padding=5, relief='groove')
        self.mainframe.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # self.mainframe.grid(row=0, column=0, sticky=self.NWES)
        # self.mainframe.columnconfigure(1, weight=1)
        # self.mainframe.rowconfigure(0, weight=1)

        upframe = ttk.Frame(self.mainframe, padding="5 5 5 5")
        upframe.grid(row=0, column=0, columnspan=3, sticky=self.NWES)
        ttk.Label(upframe, image=self.img_logo).pack(expand=False, side=tk.TOP)

    def set_icon(self):
        if 'win32' in sys.platform:
            icon_ = os.path.join(config.CODEPATH, 'res', 'icon3.ico')
            self.root.iconbitmap(default=icon_)
        elif 'linux' in sys.platform:
            img_ = tk.Image('photo', file=os.path.join(config.CODEPATH, 'res', 'icon3.png'))
            self.root.tk.call('wm', 'iconphoto', self.root._w, img_)

    def mainloop(self):
        self.root.mainloop()

    def quit_app(self, event=None):
        self.root.withdraw()
        self.root.destroy()

    @threaded
    def set_output(self):
        choose_dir = self.get_dir(path='default_path')
        if choose_dir and os.path.isdir(choose_dir):
            self.OUTPUT.set(os.path.realpath(choose_dir))

    def about_msg(self):
        messages.about_msg()

    @staticmethod
    def get_monospace_font():
        return {
            'linux': font.Font(size=9, family='Monospace'),
            'win32': font.Font(size=9, family='Consolas'),
            'darwin': font.Font(size=11, family='Menlo')
        }.get(sys.platform, font.Font(size=9, family='Monospace'))

    def get_file(self, fname, ftype=[], fsize=0, fsizes=[], lpath='last_path'):
        filetypes = [("All files", "*")]
        options = {'initialfile': fname, 'initialdir': self.conf(lpath)}
        if not self.conf.is_mac:
            options['filetypes'] = ftype + filetypes
        dialog = filedialog.askopenfilename(**options)
        if dialog and os.path.isfile(dialog):
            size_ = os.path.getsize(dialog)
            if fsize and (size_ != fsize):
                raise FileHandlerError(f'The file selected is {size_} bytes, but {fsize} is expected.')
            if fsizes and (size_ not in fsizes):
                raise FileHandlerError('The file selected is of unexpected size.')
            path_ = os.path.split(dialog)[0]
            self.conf.update_conf(**{'DEFAULT': {lpath: path_}})
            dialog = os.path.realpath(dialog)
            return dialog

    def get_dir(self, path='last_path'):
        dialog = filedialog.askdirectory(initialdir=self.conf(path))
        if dialog:
            dialog = os.path.realpath(dialog)
            self.conf.update_conf(**{'DEFAULT': {'last_path': dialog}})
            return dialog


# Main Window -----------------------------------------------------------------
class MainWindow(BaseWindow):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title()
        # ADB moved to the bottom once the logger handler is configured
        # self.adb = adb_conn.ADBConn(logger=logger, log_level=self.log_level)
        self.registry = decoders.Registry()
        self.menubar = tk.Menu(self.root, tearoff=0)
        self.root['menu'] = self.menubar
        self.build_file_menus()
        self.build_decoders_menus()
        self.build_utils_menus()
        self.build_locks_menus()
        self.build_tools_menus()
        self.build_adb_menus()
        self.build_help_menus()

        self.DeviceStatus = tk.StringVar()
        self.StatusMsg = tk.StringVar()
        self.StatusMsg.set('Ready')

        # MIDFRAME -----------------------------------------------------------
        midframe = ttk.Frame(self.mainframe, padding=(5, 5, 5, 5))
        midframe.grid(row=1, column=0, columnspan=2, sticky=self.NWES)
        # Output folder
        opframe = ttk.Labelframe(midframe,
            text='Global Output Location (Decoders / Extraction / Parsing)',
            padding=(5, 0, 0, 5))
        opframe.pack(fill=tk.X, expand=0, side=tk.TOP)
        self.output_button = ttk.Button(opframe, text="Output..", command=self.set_output)
        self.output_button.pack(side=tk.LEFT)
        createToolTip(self.output_button, 'Select the output location where data will be saved to')
        ttk.Label(opframe, textvariable=self.OUTPUT, padding=(5, 0))\
            .pack(expand=True, fill=tk.X, side=tk.LEFT)

        noteframe = ttk.Notebook(midframe, padding=(1, 0))
        noteframe.pack(fill=tk.X, expand=0, side=tk.TOP)

        # ADB extract controls
        extract_adb_frame = ttk.Frame(noteframe, padding=(5, 0))
        noteframe.add(extract_adb_frame, text='Extraction (USB)')
        self.check_button = ttk.Button(extract_adb_frame, text='Check')
        self.check_button.bind('<Button-1>', self.check_usb)
        createToolTip(self.check_button, 'Check if any Android devices are connected')
        self.check_button.grid(row=1, column=0, sticky=tk.W)
        ttk.Label(extract_adb_frame, font=self.FontStatus, textvariable=self.DeviceStatus, padding=(5, 0))\
            .grid(row=1, column=1, sticky=tk.W)

        self.extract_button = ttk.Button(extract_adb_frame, text='Extract')
        self.extract_button.bind('<Button-1>', self.RunUsbExtraction)
        self.extract_button.grid(row=2, column=0, sticky=tk.W)
        createToolTip(self.extract_button, 'Extract and decode data from a connected Android device')

        # self.open_report = tk.IntVar()
        # self.open_report.set(1)
        # self.open_report_button = ttk.Checkbutton(extract_adb_frame, text='Open REPORT.html in browser', var=self.open_report)
        # self.open_report_button.grid(row=3, column=0, columnspan=2, sticky=tk.W)
        # createToolTip(self.open_report_button, 'On successful extraction open the result in the browser')

        self.force_backup = tk.IntVar()
        self.force_backup_button = ttk.Checkbutton(extract_adb_frame, text='Use AB method (ignore root)', var=self.force_backup)
        self.force_backup_button.grid(row=4, column=0, columnspan=2, sticky=tk.W)
        createToolTip(self.force_backup_button, 'If rooted - force Android Backup extraction instead')

        self.extract_shared = tk.IntVar()
        self.extract_shared_button = ttk.Checkbutton(extract_adb_frame, text='Extract Shared Storage', var=self.extract_shared)
        self.extract_shared_button.grid(row=5, column=0, columnspan=2, sticky=tk.W)
        createToolTip(self.extract_shared_button, 'File system extraction of shared storage\n(Pictutes, Videos, Audios, other files)')

        # Forder extract controls
        extract_folder_frame = ttk.Frame(noteframe, padding=(5, 0))
        noteframe.add(extract_folder_frame, text='Parse (Folder)')
        self.extract_folder = ttk.Button(extract_folder_frame, text='Directory..', )
        self.extract_folder.grid(row=1, column=0, sticky=tk.W)
        self.extract_folder.bind('<Button-1>', self.RunDirExtraction)
        createToolTip(self.extract_folder, "Choose the '/data/data' directory to be parsed and data decoded")

        # TAR extract controls
        extract_tar_frame = ttk.Frame(noteframe, padding=(5, 0))
        noteframe.add(extract_tar_frame, text='Parse (.TAR)')
        self.extract_tar = ttk.Button(extract_tar_frame, text='TAR File..', )
        self.extract_tar.bind('<Button-1>', self.RunTarExtraction)
        self.extract_tar.grid(row=1, column=0, sticky=tk.W)
        createToolTip(self.extract_tar, "Choose the 'data.tar' backup file to be parsed and data decoded")

        # AB extract controls
        extract_backup_frame = ttk.Frame(noteframe, padding=(5, 0))
        noteframe.add(extract_backup_frame, text='Parse (.AB)')
        self.extract_backup = ttk.Button(extract_backup_frame, text='AB File..', )
        self.extract_backup.bind('<Button-1>', self.RunAbExtraction)
        self.extract_backup.grid(row=1, column=0, sticky=tk.W)
        createToolTip(self.extract_backup, "Choose the 'backup.ab' file to be parsed and data decoded")

        # LOG FRAME --------------------------------------------------------
        textframe = ttk.Frame(self.mainframe)
        textframe.grid(row=2, column=0, columnspan=2, sticky=self.NWES)

        # Text Field + logger
        self.TF = tk.Text(
            textframe, font=self.FontMono, wrap=tk.WORD, width=65,
            bg='white', height=self.conf('window_size'))
        self.TF.bind('<Button-3>', rClicker, add='')
        self.TF.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.set_logger()

        # Scrolling
        vs = ttk.Scrollbar(textframe, orient=tk.VERTICAL)
        vs.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        vs['command'] = self.TF.yview
        self.TF['yscrollcommand'] = vs.set
        # Bottom buttons
        clear_field = ttk.Button(self.mainframe, text='Clear Log', command=self.clear_log)
        clear_field.grid(row=3, column=0, sticky=tk.W)
        save_log = ttk.Button(self.mainframe, text='Save Log', command=self.save_log)
        save_log.grid(row=3, columnspan=2, sticky=tk.E)

        # STATUS UPDATE --------------------------------------------------------
        downframe = ttk.Frame(self.mainframe, relief='groove')
        downframe.grid(row=4, column=0, columnspan=2, sticky=self.NWES)

        self.StatusMsgLabel = ttk.Label(downframe, relief='flat', padding=(5, 1),
            font=self.FontStatus, textvariable=self.StatusMsg)
        self.StatusMsgLabel.grid(row=4, column=0, sticky=tk.W, padx=5, pady=3)
        self.StatusMsgLabel.configure(background='light green')

        # STARTUP & TIME SETTINGS
        logger.info(f'Started: {__app_name__} {__version__}')
        logger.info(f"Time settings/format: {self.conf('date_format')}")
        logger.info(f"Detected/PC time: {self.time_now_local}")
        logger.info(f"Universal time:   {self.time_now_utc}")
        logger.info(f"Time in reports:  {self.time_now_configured} <--")  # \u2190
        self.conf.check_latest_version(logger=self.logger)

        # Setup ADB
        # def setup_adb(self):
        self.adb = adb_conn.ADBConn(logger=logger, log_level=self.log_level)

    @property
    def time_now_local(self):
        now = datetime.datetime.now()
        return now.strftime(self.conf.date_format)

    @property
    def time_now_configured(self):
        now = datetime.datetime.now(self.conf.tzone)
        return now.strftime(self.conf.date_format)

    @property
    def time_now_utc(self):
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=0)))
        return now.strftime(self.conf.date_format)

    def set_logger(self):
        logging.basicConfig(level=self.log_level)
        log_handler = TextFieldHandler(self.TF, level=self.log_level)
        logger.addHandler(log_handler)
        self.logger = logger

    def set_title(self):
        title = f'{__app_name__} - {__version__}'
        self.root.title(title)

    def clear_log(self):
        if messagebox.askyesno(
                message='Are you sure you want to clear the log?',
                icon='question',
                title='Clear log'):
            self.TF.delete('1.0', tk.END)

    def save_log(self):
        dialog = filedialog.asksaveasfilename(
            initialdir=self.conf('default_path'),
            initialfile='andriller.log',
            filetypes=[('Log files', '*.log')])
        if dialog:
            with open(dialog, 'w', encoding='UTF-8') as W:
                W.write(self.TF.get('1.0', tk.END))

    # Menu generators ---------------------------------------------------------

    def build_file_menus(self):
        menu_file = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_file, label='File', underline=0)
        menu_file.add_command(label='Save log', underline=0, command=self.save_log)
        menu_file.add_command(label='Clear log', underline=0, command=self.clear_log)
        menu_file.add_command(label='Preferences', command=self.preferences)
        menu_file.add_separator()
        menu_file.add_command(label='Exit', underline=1, command=self.root.destroy, accelerator='Esc * 2')

    def set_decoder(self, decoder):
        name_ = f'menu_{decoder.__name__}'
        setattr(self, name_, decoder)
        return getattr(self, name_)

    def build_decoders_menus(self):
        menu_dec = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_dec, label='Decoders', underline=0)
        for decoder in sorted(self.registry.decoders, key=lambda d: d.__name__):
            dec = decoder.staged()
            if dec.exclude_from_menus:
                continue
            action = lambda x = dec: self.decode_file(x)
            label = f'{dec.title} ({dec.TARGET or dec.RETARGET})..'
            menu_dec.add_command(label=label, command=action)

    def build_help_menus(self):
        menu_help = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_help, label='Help', underline=0)
        menu_help.add_command(label='Visit website')
        menu_help.add_separator()
        menu_help.add_command(label='Run Update', command=lambda: self.conf.upgrade_package(logger=self.logger))
        menu_help.add_separator()
        menu_help.add_command(label='About', command=self.about_msg)

    def build_adb_menus(self):
        menu_adb = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_adb, label='ADB', underline=0)
        for mode in ['', *adb_conn.ADBConn.MODES.keys()]:
            label_ = f"Reboot: {mode.title() or 'Normal'}"
            action = lambda x = mode: self.adb.reboot(mode=x)
            menu_adb.add_command(label=label_, command=action)

    def build_utils_menus(self):
        menu_utils = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_utils, label='Apps Utils', underline=5)
        # menu_utils.add_separator()
        menu_utils.add_command(label="WhatsApp Crypt", command=self.whatsapp_crypt)

    def build_locks_menus(self):
        menu_locks = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_locks, label='Lockscreens', underline=0)
        menu_locks.add_command(label='Gesture Pattern (Legacy)', command=self.brute_pattern)
        menu_locks.add_separator()
        menu_locks.add_command(label='PIN Cracking (Generic)', command=self.brute_gen_pin)
        menu_locks.add_command(label='Password by Dictionary (Generic)', command=self.brute_gen_dict)
        menu_locks.add_command(label='Password by Brute-Force (Generic)', command=self.brute_force_gen)
        menu_locks.add_separator()
        menu_locks.add_command(label='PIN Cracking (Samsung)', command=self.brute_sam_pin)
        menu_locks.add_command(label='Password by Dictionary (Samsung)', command=self.brute_sam_dict)
        # menu_locks.add_separator()

    def build_tools_menus(self):
        menu_tools = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_tools, label='Tools', underline=0)
        menu_tools.add_command(label='Convert AB to TAR file..', command=self.ab_to_tar)
        menu_tools.add_command(label='Extract AB to folder..', command=self.ab_to_folder)
        menu_tools.add_separator()
        menu_tools.add_command(label='Screen Capture', command=self.screencap)

    @threaded
    def ab_to_tar(self):
        ab_file = self.get_file('', ftype=[('AB File', '*.ab')])
        if ab_file:
            logger.info(f'Converting {ab_file}')
            self.StatusMsg.set('Converting to tar...')
            tar_ = DrillerTools.ab_to_tar(ab_file, to_tmp=False)
            logger.info(f'Converted to: {tar_}')
            self.StatusMsg.set('Finished')

    @threaded
    def ab_to_folder(self):
        ab_file = self.get_file('', ftype=[('AB File', '*.ab')])
        if ab_file:
            logger.info(f'Converting {ab_file}')
            self.StatusMsg.set('Converting to tar...')
            tar_ = DrillerTools.ab_to_tar(ab_file, to_tmp=False)
            self.StatusMsg.set('Extracting tar members...')
            dst_ = pathlib.Path(f'{ab_file}_extracted/')
            dst_.mkdir()
            for _ in DrillerTools.extract_form_tar(tar_, dst_, full=True):
                pass
            logger.info(f'Extracted to: {dst_}')
            self.StatusMsg.set('Finished')

    # Other Windows -----------------------------------------------------------
    def preferences(self):
        root = Preferences(root=self.root)
        root.mainloop()

    def whatsapp_crypt(self):
        root = WhatsAppCrypt(root=self.root)
        root.mainloop()

    def brute_pattern(self):
        root = BrutePattern(root=self.root)
        root.mainloop()

    def brute_gen_pin(self):
        root = BruteGenPin(root=self.root)
        root.mainloop()

    def brute_gen_dict(self):
        root = BruteGenDict(root=self.root)
        root.mainloop()

    def brute_sam_dict(self):
        root = BruteSamDict(root=self.root)
        root.mainloop()

    def brute_sam_pin(self):
        root = BruteSamPin(root=self.root)
        root.mainloop()

    def brute_force_gen(self):
        root = BruteForceGen(root=self.root)
        root.mainloop()

    def screencap(self):
        root = ScreenCap(root=self.root)
        root.mainloop()

    # Class functions ---------------------------------------------------------

    @threaded
    def check_usb(self, event):
        with disable_control(event):
            self.DeviceStatus.set('Please wait...')
            if not self.adb.adb_bin:
                self.DeviceStatus.set('ADB is not configured!')
                return
            self.adb('start-server')
            serial, status = self.adb.device()
            if status == 'offline':
                self.DeviceStatus.set('Device is OFFLINE!')
            elif status == 'unauthorized':
                self.DeviceStatus.set('Device is UNAUTHORIZED!')
            else:
                self.DeviceStatus.set(f'Serial ID: {serial}' if serial else 'Device not detected!')

    @threaded
    @log_errors
    def decode_file(self, decoder):
        choose_file = self.get_file(decoder.TARGET)
        if choose_file and os.path.isfile(choose_file):
            file_path = os.path.realpath(choose_file)
            logger.info(f'Decoding: {os.path.basename(file_path)}')
            work_dir = self.OUTPUT.get() or os.path.split(file_path)[0]
            dec = decoder.__class__(work_dir, file_path)
            html_rep = dec.report_html()
            report = work_dir / pathlib.Path(html_rep)
            webbrowser.open_new_tab(report.as_uri())
            dec.report_xlsx()

    @threaded
    def RunUsbExtraction(self, event):
        with disable_control(event):
            output_dir = self.OUTPUT.get()
            if not output_dir:
                messages.select_output()
            elif self.DeviceStatus.get().endswith('!'):
                messages.device_not_detected()
                return
            elif os.path.exists(output_dir):
                self.StatusMsg.set('Running...')
                drill = driller.ChainExecution(
                    output_dir,
                    status_msg=self.StatusMsg,
                    do_shared=self.extract_shared.get(),
                    use_adb=True,
                    logger=logger)
                drill.InitialAdbRead()
                drill.CreateWorkDir()
                drill.DataAcquisition(
                    run_backup=self.force_backup.get(),
                    shared=self.extract_shared.get(),)
                drill.DataExtraction()
                drill.DecodeShared()
                drill.DataDecoding()
                drill.GenerateHtmlReport()
                drill.GenerateXlsxReport()
                drill.CleanUp()

    @threaded
    def RunAbExtraction(self, event):
        with disable_control(event):
            output_dir = self.OUTPUT.get()
            if not output_dir:
                messages.select_output()
            elif os.path.exists(output_dir):
                ab_file = self.get_file('', ftype=[('AB File', '*.ab')])
                if ab_file and os.path.isfile(ab_file):
                    self.StatusMsg.set('Running...')
                    drill = driller.ChainExecution(
                        output_dir,
                        backup=ab_file,
                        status_msg=self.StatusMsg,
                        logger=logger)
                    drill.CreateWorkDir()
                    drill.DataExtraction()
                    drill.DataDecoding()
                    drill.DecodeShared()
                    drill.GenerateHtmlReport()
                    drill.GenerateXlsxReport()
                    drill.CleanUp()

    @threaded
    def RunTarExtraction(self, event=None):
        with disable_control(event):
            output_dir = self.OUTPUT.get()
            if not output_dir:
                messages.select_output()
            elif os.path.exists(output_dir):
                tar_file = self.get_file('', ftype=[('TAR File', '*.tar')])
                if tar_file and os.path.isfile(tar_file):
                    self.StatusMsg.set('Running...')
                    drill = driller.ChainExecution(
                        output_dir,
                        tarfile=tar_file,
                        status_msg=self.StatusMsg,
                        logger=logger)
                    drill.CreateWorkDir()
                    drill.DataExtraction()
                    drill.DataDecoding()
                    drill.GenerateHtmlReport()
                    drill.GenerateXlsxReport()
                    drill.CleanUp()

    @threaded
    def RunDirExtraction(self, event=None):
        with disable_control(event):
            output_dir = self.OUTPUT.get()
            if not output_dir:
                messages.select_output()
            elif os.path.exists(output_dir):
                src_dir = self.get_dir()
                if src_dir:
                    self.StatusMsg.set('Running...')
                    drill = driller.ChainExecution(
                        output_dir,
                        src_dir=src_dir,
                        status_msg=self.StatusMsg,
                        logger=logger)
                    drill.CreateWorkDir()
                    drill.ExtractFromDir()
                    drill.DataDecoding()
                    drill.GenerateHtmlReport()
                    drill.GenerateXlsxReport()
                    drill.CleanUp()


# WhatsApp Crypt --------------------------------------------------------------
class WhatsAppCrypt(BaseWindow):
    KEY_SIZE = decrypts.WhatsAppCrypt.KEY_SIZE
    SUFFIX = decrypts.WhatsAppCrypt.SUFFIX

    def __init__(self, root=None, title='WhatsApp Crypt Decryptor'):
        super().__init__(root=root, title=title)
        self.guide = statics.WHATSAPP_CRYPT
        self.work_dir = None
        self.crypts = {}
        self.key_file = None
        self.supported = self.get_supported()
        self._info = tk.StringVar()
        self._info_but = tk.StringVar()
        self._info_but.set('Show Info')

        ttk.Label(self.mainframe, text=title, font=self.FontTitle).grid(row=1, column=0, columnspan=2)
        tk.Button(self.mainframe, textvariable=self._info_but, relief='flat', command=self.info_toggle)\
            .grid(row=1, column=2, columnspan=1, sticky=tk.E)
        ttk.Label(self.mainframe, textvar=self._info).grid(row=5, column=0, columnspan=3, sticky=self.WE)

        self.dir_label = tk.StringVar()
        self.dir_but = ttk.Button(self.mainframe, text='Select directory', command=self.set_dir)
        self.dir_but.grid(row=10, column=0, columnspan=1, sticky=tk.W)
        ttk.Label(self.mainframe, textvar=self.dir_label).grid(row=10, column=1, columnspan=2, sticky=tk.W)

        self.key_label = tk.StringVar()
        self.key_but = ttk.Button(self.mainframe, text="Select 'key' file", command=self.set_key)
        self.key_but.grid(row=11, column=0, columnspan=1, sticky=tk.W)
        ttk.Label(self.mainframe, textvar=self.key_label).grid(row=11, column=1, columnspan=2, sticky=tk.W)

        self.file_box = ttk.Treeview(self.mainframe, columns=['size', 'done'], selectmode=tk.EXTENDED)
        self.file_box.heading('#0', text='File Name')
        self.file_box.heading('size', text='Size')
        self.file_box.heading('done', text='Decrypted')
        self.file_box.column('size', width=30)
        self.file_box.column('done', width=20)
        self.file_box.tag_configure('success', background='light green')
        self.file_box.tag_configure('failure', background='#ff8080')
        self.file_box.grid(row=20, column=0, columnspan=3, sticky=self.WE)

        self.dec_all = ttk.Button(self.mainframe, text='Decrypt All', command=self.decrypt_all)
        self.dec_all.grid(row=30, column=0, sticky=tk.W)
        self.dec_sel = ttk.Button(self.mainframe, text='Decrypt Selected', command=self.decrypt_sel)
        self.dec_sel.grid(row=30, column=2, sticky=tk.E)

    def info_toggle(self):
        (self._info.set(''), self._info_but.set('Show Info')) if self._info.get() \
            else (self._info.set(statics.WHATSAPP_CRYPT), self._info_but.set('Hide Info'))

    def controls_state(self, state):
        for c in [self.dir_but, self.key_but, self.dec_all, self.dec_sel]:
            c.configure(state=state)

    def set_dir(self):
        dialog = self.get_dir()
        if dialog:
            self.work_dir = dialog
            self.dir_label.set(self.work_dir)
            self.check_dir()
            self.try_key_file()

    def set_key(self, key=None):
        dialog = key or self.get_file('key', fsize=self.KEY_SIZE)
        if dialog:
            self.key_file = None
            self.key_label.set('')
            self.key_file = dialog
            self.key_label.set(self.key_file)

    def try_key_file(self):
        key = os.path.join(self.work_dir, 'key')
        if os.path.isfile(key) and os.path.getsize(key) == self.KEY_SIZE:
            logger.info('WhatsAppCrypt: key file was detected & automatically selected')
            self.set_key(key=key)

    def check_dir(self):
        self.crypts.clear()
        self.file_box.delete(*self.file_box.get_children())
        path_ = os.path.join(self.work_dir, '*.crypt*')
        for f in glob.iglob(path_):
            done = os.path.exists(f'{os.path.splitext(f)[0]}{self.SUFFIX}')
            size = human_bytes(os.path.getsize(f))
            item = self.file_box.insert('', tk.END, text=os.path.basename(f), values=[size, done])
            self.crypts[item] = f

    def tree_update(self, iid, values):
        self.file_box.item(iid, values=values)

    def decrypt_all(self):
        self.file_box.selection_add(self.file_box.get_children())
        self.decrypt_sel()

    def decrypt_sel(self):
        sel = self.file_box.selection()
        if not sel:
            messagebox.showwarning('No selection made', 'Select at least one database to decrypt.')
        self.run_decrypt(sel)

    def run_decrypt(self, sel):
        try:
            self.controls_state(tk.DISABLED)
            for i in sel:
                file_ = self.crypts[i]
                fname = os.path.basename(file_)
                file_ext = file_.split('.')[-1].lower()
                decrypter = self.supported.get(file_ext)
                if decrypter:
                    try:
                        wadec = decrypter(file_, self.key_file)
                        if wadec.decrypt():
                            vals = self.file_box.item(i)['values']
                            vals[1] = True
                            self.file_box.item(i, values=vals, tags='success')
                            logger.info(f'WhatsAppCrypt: {fname} successfully decrypted.')
                    except decrypts.WhatsAppCryptError as err:
                        logger.error(f'WhatsAppCrypt: {err}')
                        self.file_box.item(i, tags='failure')
                        messagebox.showerror('WhatsApp decryption error', str(err))
                    except Exception as err:
                        logger.error(f'WhatsAppCrypt: {fname}: {err}')
                        self.file_box.item(i, tags='failure')
        finally:
            self.file_box.selection_set()
            self.controls_state(tk.NORMAL)

    def get_supported(self):
        return {kls.CRYPT: kls for kls in decrypts.WhatsAppCrypt.__subclasses__()}


# Pattern Decoding Window -----------------------------------------------------
class BrutePattern(BaseWindow):
    CANVAS_SIZE = 210
    FACTOR = 3

    def __init__(self, root=None, title='Lockscreen Gesture Pattern'):
        super().__init__(root=root, title=title)

        ttk.Label(self.mainframe, font=self.FontTitle, text=f'\n{title}\n').grid(row=1, column=0, columnspan=3)
        self.FILE = tk.StringVar()
        self.HASH = tk.StringVar()
        self.PATTERN = tk.StringVar()

        browse = ttk.Button(self.mainframe, text='Browse', command=self.select_file)
        browse.grid(row=2, column=0, sticky=tk.E)
        createToolTip(browse, "Select 'gesture.key' and it will be decoded automatically.")
        ttk.Label(self.mainframe, textvariable=self.FILE).grid(row=2, column=1, columnspan=2, sticky=tk.W)

        ttk.Label(self.mainframe, text='or').grid(row=3, column=0, sticky=tk.E)
        hash_label = ttk.Label(self.mainframe, text='Gesture Hash: ')
        hash_label.grid(row=4, column=0, sticky=tk.E)
        createToolTip(hash_label, "Enter gesture.key hash value (40 hexadecimal characters) from:\n-->  '/data/system/gesture.key'")
        hash_field = ttk.Entry(self.mainframe, font=self.FontMono, textvariable=self.HASH, width=45)
        hash_field.grid(row=4, column=1, columnspan=2, sticky=tk.W)
        hash_field.bind('<Button-3>', rClicker, add='')
        pattern_label = ttk.Label(self.mainframe, text='Pattern: ')
        pattern_label.grid(row=6, column=0, sticky=tk.E)
        createToolTip(pattern_label, 'Double click on the entry field to edit and then to Draw\nEnter as a list of integers, eg: [8,4,0,1,2]')
        result_field = ttk.Entry(self.mainframe, textvariable=self.PATTERN, font=self.FontTitle, width=25, state='disabled')
        result_field.bind('<Button-3>', rClicker, add='')
        result_field.bind('<Button-1>', lambda e: result_field.configure(state='normal'))
        result_field.bind('<B3-Motion>', lambda e: result_field.configure(state='normal'))
        result_field.bind('<FocusOut>', lambda e: result_field.configure(state='disabled'))
        result_field.grid(row=6, column=1, columnspan=2, sticky=tk.W)

        self.VISUAL = tk.Canvas(self.mainframe, width=self.CANVAS_SIZE, height=self.CANVAS_SIZE, borderwidth=0)
        self.VISUAL.grid(row=7, column=1, sticky=tk.W)
        self.draw_pattern(self.VISUAL, self.PATTERN.get())

        decode_button = ttk.Button(self.mainframe, text='Decode', command=self.crack_pattern)
        decode_button.grid(row=10, column=0, sticky=tk.E)
        draw_button = ttk.Button(self.mainframe, text='Draw', command=lambda: self.draw_pattern(self.VISUAL, self.PATTERN.get()))
        draw_button.grid(row=10, column=1, columnspan=2, sticky=tk.W)
        ttk.Button(self.mainframe, text='Close', command=self.root.destroy).grid(row=10, column=2, sticky=tk.E)

    # Pattern drawing code
    def draw_pattern(self, widget, pattern=None):
        POS = []

        def checkered(canvas, line_distance):
            for x in range(line_distance, self.CANVAS_SIZE, line_distance):
                canvas.create_line(x, 0, x, self.CANVAS_SIZE, fill="#999999")
            for y in range(line_distance, self.CANVAS_SIZE, line_distance):
                canvas.create_line(0, y, self.CANVAS_SIZE, y, fill="#999999")

        def numbered(canvas):
            n = 0
            step = self.CANVAS_SIZE // self.FACTOR
            start = step // 2
            stepx = start
            for _ in range(self.FACTOR):
                stepy = start
                while stepy < self.CANVAS_SIZE:
                    canvas.create_oval(
                        stepy + (self.CANVAS_SIZE // 15),
                        stepx + (self.CANVAS_SIZE // 15),
                        stepy - (self.CANVAS_SIZE // 15),
                        stepx - (self.CANVAS_SIZE // 15),
                        fill='#444444', outline='#444444')
                    canvas.create_text(
                        stepy,
                        stepx,
                        font=(self.CANVAS_SIZE // 10),
                        text=str(n),
                        fill='#FFFFFF')
                    POS.append((stepy, stepx))
                    n += 1
                    stepy += step
                stepx += step

        def clean_pat(pattern):
            try:
                return json.loads(pattern)
            except Exception as e:
                logger.warning(f'{e}')
                return []

        def draw(canvas, pattern=[]):
            canvas.delete(tk.ALL)
            self.draw_pattern(self.VISUAL, None)
            if pattern:
                combo = list(itertools.chain(*[POS[_] for _ in clean_pat(pattern)]))
                if combo:
                    canvas.create_line(
                        combo,
                        arrow='last',
                        arrowshape=[
                            self.CANVAS_SIZE // 25,
                            self.CANVAS_SIZE // 20,
                            self.CANVAS_SIZE // 40
                        ],
                        width=(self.CANVAS_SIZE // 70),
                        fill='#00CC00')

        checkered(widget, self.CANVAS_SIZE // self.FACTOR)
        numbered(widget)
        if pattern:
            draw(widget, pattern)

    def select_file(self):
        selection = filedialog.askopenfilename(
            initialdir=self.conf('last_path'),
            initialfile='gesture.key',
            filetypes=[('Key file', '*.key'), ('Any file', '*')])
        if selection and os.path.isfile(selection):
            file_path = os.path.realpath(selection)
            if os.path.getsize(file_path) != 20:
                return  # TODO: error message
            self.conf.update_conf(**{'DEFAULT': {'last_path': os.path.dirname(file_path)}})
            with open(file_path, 'rb') as R:
                self.HASH.set(binascii.hexlify(R.read()).decode())
            self.crack_pattern()

    @threaded
    def crack_pattern(self):
        # '6a062b9b3452e366407181a1bf92ea73e9ed4c48'
        sha = self.HASH.get().strip()
        if len(sha) != 40:
            return  # TODO: error message
        self.VISUAL.delete(tk.ALL)
        self.draw_pattern(self.VISUAL, None)
        self.PATTERN.set('Decoding...')
        pat = cracking.crack_pattern(sha)
        if pat:
            pat = str(pat)
            self.PATTERN.set(pat)
            self.draw_pattern(self.VISUAL, pat)
        else:
            self.PATTERN.set(':(')


# Generic PIN Cracking Window -------------------------------------------------
class LockscreenBase(BaseWindow):
    def __init__(self, root=None, title=None, logger=logger):
        self.logger = logger
        super().__init__(root=root, title=title)

        ttk.Label(self.mainframe, font=self.FontTitle, text=f'\n{title}\n').grid(row=1, column=0, columnspan=3)

        self.START = tk.StringVar()
        self.END = tk.StringVar()
        self.START.set('0000')
        self.END.set('9999')
        self.HASH = tk.StringVar()
        self.SALT = tk.IntVar()
        self.SALT.set('')
        self.RESULT = tk.StringVar()
        self.DICTFILE = tk.StringVar()
        self.DICTLAB = tk.StringVar()
        self.TRIED = tk.StringVar()
        self.RATE = tk.StringVar()
        self.PROG = tk.StringVar()
        self.STOP = tk.BooleanVar()
        self.stats_enabled = False
        self.prog_enabled = False

        self.menubar = tk.Menu(self.root, tearoff=0)
        self.root['menu'] = self.menubar
        menu_read = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(menu=menu_read, label='Read..', underline=0)
        menu_read.add_command(label="Salt from 'settings.db'...", command=self.salt_settings)
        menu_read.add_command(label="Salt from 'locksettings.db'...", command=self.salt_locksettings)
        menu_read.add_command(label="Salt from 'locksettings.db-wal'...", command=self.salt_locksettings_wal)
        menu_read.add_command(label="Hash from 'password.key'...", command=self.password_read)

        # Hash - 4
        hash_label = ttk.Label(self.mainframe, text='Password Hash: ')
        hash_label.grid(row=40, column=0, sticky=tk.E)
        hash_field = ttk.Entry(self.mainframe, font=self.FontMono, textvariable=self.HASH, width=40)
        hash_field.grid(row=40, column=1, columnspan=2, sticky=tk.W)

        # Salt - 5
        salt_label = ttk.Label(self.mainframe, text='Salt (integer): ')
        salt_label.grid(row=50, column=0, sticky=tk.E)
        salt_field = ttk.Entry(self.mainframe, font=self.FontMono, textvariable=self.SALT, width=20)
        salt_field.grid(row=50, column=1, columnspan=2, sticky=tk.W)

        # Results - 6
        ttk.Label(self.mainframe, text='Result: ').grid(row=60, column=0, sticky=tk.E)
        self.result_field = ttk.Label(self.mainframe, textvariable=self.RESULT, font=self.FontTitle, foreground='grey')
        self.result_field.grid(row=60, column=1, columnspan=2, sticky=tk.W)

        # Controls - 8
        self.start_button = ttk.Button(self.mainframe, text='Start', command=self.start)
        # self.start_button.bind('<Button-1>', self.start)
        self.start_button.grid(row=80, column=0, sticky=tk.E)
        self.stop_button = ttk.Button(self.mainframe, text='Stop', command=lambda: self.STOP.set(1))
        self.stop_button.config(state=tk.DISABLED)
        self.stop_button.grid(row=80, column=1, columnspan=2, sticky=tk.W)
        self.close_button = ttk.Button(self.mainframe, text='Close', command=self.root.destroy)
        self.close_button.grid(row=80, column=2, sticky=tk.E)

    def salt_settings(self, key='lockscreen.password_salt'):
        dialog = self.get_file(
            'settings.db',
            ftype=[('SQLite Databases', '*.db')])
        if dialog:
            dec = decoders.SettingsDecoder(None, dialog)
            salt_value = dec.DICT.get(key)
            if salt_value:
                logger.info(f'Lockscreen salt: {salt_value}')
                self.SALT.set(salt_value)
            else:
                messagebox.showwarning(
                    'Value not found',
                    f'`{key}` not found in the file!')

    def salt_locksettings(self, key='lockscreen.password_salt'):
        dialog = self.get_file(
            'locksettings.db',
            ftype=[('SQLite Databases', '*.db')])
        if dialog:
            try:
                dec = decoders.LocksettingsDecoder(None, dialog)
                salt_value = dec.DICT.get(key)
                if salt_value:
                    logger.info(f'Lockscreen salt: {salt_value}')
                    self.SALT.set(salt_value)
            except Exception:
                messagebox.showwarning(
                    'Value not found',
                    f'`{key}` not found in the database!\nTry parsing the `locksettings.db-wal` instead.')

    def salt_locksettings_wal(self):
        dialog = self.get_file(
            'locksettings.db-wal',
            ftype=[('SQLite Write Ahead Logs', '*.db-wal')])
        if dialog and os.path.getsize(dialog):
            salt_values = decoders.parse_lockscreen_wal(dialog)
            if len(salt_values) == 1:
                logger.info(f'Lockscreen salt: {salt_values[0]}')
                self.SALT.set(salt_values[0])
            elif len(salt_values) > 1:
                for n, s in enumerate(salt_values, start=1):
                    logger.info(f'Lockscreen salt_{n}: {s}')
                messagebox.showwarning(
                    'Multiple results found',
                    'More than one value for salt was found! Check the log window to pick a value manually.')
            else:
                messagebox.showwarning(
                    'Value not found',
                    'Salt was not found in the file!')

    def password_read(self):
        try:
            file_ = self.get_file('password.key', ftype=[('Password File', '*.key')], fsizes=[40, 72])
            if file_:
                with open(file_, 'r') as R:
                    hash_val = R.read()
                    logger.info(f'Password hash: {hash_val}')
                    self.HASH.set(hash_val)
        except FileHandlerError as err:
            messagebox.showwarning('Wrong file size', str(err))
        except UnicodeDecodeError:
            messagebox.showwarning(
                'Wrong file type', 'The file is binary, not suitable.')

    def enable_pin_range(self):
        self.start_label = ttk.Label(self.mainframe, text='Start from: ')
        createToolTip(self.start_label, "Start the PIN from (Recommended: 0000)")
        self.start_field = ttk.Entry(self.mainframe, textvariable=self.START, width=16)
        self.start_field.bind('<Button-3>', rClicker, add='')
        self.start_label.grid(row=20, column=0, sticky=tk.E)
        self.start_field.grid(row=20, column=1, columnspan=2, sticky=tk.W)

        self.end_label = ttk.Label(self.mainframe, text='Max value: ')
        createToolTip(self.end_label, "Maximum PIN value")
        self.end_field = ttk.Entry(self.mainframe, textvariable=self.END, width=16)
        self.end_field.bind('<Button-3>', rClicker, add='')
        self.end_label.grid(row=30, column=0, sticky=tk.E)
        self.end_field.grid(row=30, column=1, columnspan=2, sticky=tk.W)

    def enable_wordlist(self):
        self.word_label = ttk.Label(self.mainframe, text='Word List File: ')
        self.word_label.grid(row=20, column=0, sticky=tk.E)
        createToolTip(self.word_label, "Select a Word List file (text file containing passwords)")
        dict_button = ttk.Button(self.mainframe, text='Browse', command=self.select_wordlist)
        dict_button.grid(row=20, column=1, sticky=tk.W)
        dict_label = ttk.Label(self.mainframe, textvariable=self.DICTLAB, font=self.FontInfo)
        dict_label.grid(row=20, column=2, columnspan=1, sticky=tk.W)

    def select_wordlist(self):
        dialog = self.get_file('', lpath='dict_path')
        if dialog and os.path.isfile(dialog):
            dialog = os.path.realpath(dialog)
            self.DICTFILE.set(dialog)
            self.DICTLAB.set(os.path.split(dialog)[1])

    def enable_alpha_range(self):
        self.MIN = tk.IntVar()
        self.MIN.set(4)
        self.MAX = tk.IntVar()
        self.MAX.set(6)
        self.LOWER = tk.IntVar()
        self.UPPER = tk.IntVar()
        self.DIGITS = tk.IntVar()
        self.CUSTOM = tk.IntVar()
        self.CUSTVALS = tk.StringVar()

        min_label = ttk.Label(self.mainframe, text='Length min/max: ')
        min_label.grid(row=20, column=0, sticky=tk.E)
        createToolTip(min_label, 'Select minimum and maximum password length')
        lframe = ttk.Frame(self.mainframe)
        lframe.grid(row=20, column=1, sticky=tk.W)
        self.min_value = tk.Spinbox(lframe, from_=1, to=16, textvariable=self.MIN, width=3, command=self.updatemin)
        createToolTip(self.min_value, "Minimum password length")
        self.min_value.pack(side=tk.LEFT)
        self.max_value = tk.Spinbox(lframe, from_=1, to=16, textvariable=self.MAX, width=3, command=self.updatemax)
        createToolTip(self.max_value, "Maximum password length")
        self.max_value.pack()

        char_label = ttk.Label(self.mainframe, text='Characters: ')
        char_label.grid(row=30, column=0, sticky=tk.E)
        createToolTip(char_label, "Choose characters combination for the password")
        iframe = ttk.Frame(self.mainframe)
        iframe.grid(row=30, column=1, sticky=tk.W)
        ttk.Checkbutton(iframe, text='Lowercase [a-z]', var=self.LOWER).pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        ttk.Checkbutton(iframe, text='Uppercase [A-Z]', var=self.UPPER).pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        ttk.Checkbutton(iframe, text='Digits [0-9]', var=self.DIGITS).pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        ttk.Checkbutton(iframe, text='Custom:', var=self.CUSTOM).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Entry(iframe, textvariable=self.CUSTVALS, width=15).pack(fill=tk.BOTH, expand=True)

    def updatemin(self):
        if self.MIN.get() > self.MAX.get():
            self.MAX.set(self.MAX.get() + 1)
        _max = self.MAX.get()
        _max = _max + 1 if _max < 16 else 16
        self.min_value.config(to_=_max)

    def updatemax(self):
        if self.MIN.get() > self.MAX.get():
            self.MIN.set(self.MIN.get() - 1)
        self.max_value.config(from_=self.MIN.get() - 1)

    def enable_stats(self):
        self.stats_enabled = True
        ttk.Label(self.mainframe, text='Words tried: ').grid(row=70, column=0, sticky=tk.E)
        ttk.Label(self.mainframe, textvariable=self.TRIED).grid(row=70, column=1, columnspan=2, sticky=tk.W)
        ttk.Label(self.mainframe, text='Rate (pw/sec): ').grid(row=71, column=0, sticky=tk.E)
        ttk.Label(self.mainframe, textvariable=self.RATE).grid(row=71, column=1, columnspan=2, sticky=tk.W)

    def enable_progress(self):
        self.prog_enabled = True
        ttk.Label(self.mainframe, text='Progress: ').grid(row=75, column=0, sticky=tk.E)
        ttk.Label(self.mainframe, textvariable=self.PROG).grid(row=75, column=1, columnspan=2, sticky=tk.W)

    @threaded
    def start(self, **kwargs):
        self.result_field.configure(foreground='grey')
        try:
            self.menubar.entryconfig(0, state=tk.DISABLED)
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.close_button.configure(state=tk.DISABLED)
            crack = cracking.PasswordCrack(
                self.HASH.get(), self.SALT.get(),
                start=self.START.get(), end=self.END.get(),
                update_rate=int(self.conf('update_rate')), **kwargs)
            result = crack.crack_password(
                self.RESULT,
                self.STOP,
                self.TRIED if self.stats_enabled else None,
                self.RATE if self.stats_enabled else None,
                self.PROG if self.prog_enabled else None)
            if result:
                self.result_field.configure(foreground='red')
                self.RESULT.set(result)
                logger.info(f'Lockscreen credential found: {result}')
            else:
                self.result_field.configure(foreground='black')
                self.RESULT.set('Stopped!' if self.STOP.get() else 'Not found!')
        except Exception as err:
            self.logger.exception('Error in password cracking.')
            messagebox.showwarning('Error', str(err))
        finally:
            self.STOP.set(0)
            self.menubar.entryconfig(0, state=tk.NORMAL)
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)
            self.close_button.configure(state=tk.NORMAL)


# --------------------------------------------------------------------------- #
class BruteGenPin(LockscreenBase):
    def __init__(self, root=None, title='Lockscreen PIN Cracking (Generic)'):
        super().__init__(root=root, title=title)
        self.enable_pin_range()


class BruteSamPin(BruteGenPin):
    def __init__(self, root=None, title='Lockscreen PIN Cracking (Samsung)'):
        super().__init__(root=root, title=title)

    def start(self, samsung=True):
        super().start(samsung=samsung)


class BruteGenDict(LockscreenBase):
    def __init__(self, root=None, title='Lockscreen Password by Dictionary (Generic)'):
        super().__init__(root=root, title=title)
        self.enable_wordlist()
        self.enable_stats()

    def start(self):
        dict_file = self.DICTFILE.get()
        super().start(alpha=True, dict_file=dict_file)


class BruteSamDict(LockscreenBase):
    def __init__(self, root=None, title='Lockscreen Password by Dictionary (Samsung)'):
        super().__init__(root=root, title=title)
        self.enable_wordlist()
        self.enable_stats()

    def start(self):
        dict_file = self.DICTFILE.get()
        super().start(alpha=True, samsung=True, dict_file=dict_file)


class BruteForceGen(LockscreenBase):
    def __init__(self, root=None, title='Lockscreen Password by Brute-Force (Generic)'):
        super().__init__(root=root, title=title)
        self.enable_alpha_range()
        self.enable_stats()
        self.enable_progress()

    def make_range(self):
        selection = ''.join([k for k, v in {
            string.ascii_lowercase: self.LOWER.get(),
            string.ascii_uppercase: self.UPPER.get(),
            string.digits: self.DIGITS.get(),
            self.CUSTVALS.get(): self.CUSTOM.get(),
        }.items() if v])
        return selection

    def start(self):
        super().start(alpha=True, alpha_range=self.make_range(),
            min_len=self.MIN.get(), max_len=self.MAX.get())


# --------------------------------------------------------------------------- #
class ScreenCap(BaseWindow):

    def __init__(self, root=None, title=f'{__app_name__}: Screen Capture'):
        super().__init__(root=root, title=title)

        self.store = screencap.ScreenStore()

        self.REPCOUNT = tk.StringVar()
        self.REPCOUNT.set('Report')
        self.OUTPUTLAB = tk.StringVar()
        self.OUTPUTLAB.set('(Not saving screen shots)')
        self.REMEMBER = tk.IntVar()
        self.REMEMBER.set(0)

        ttk.Label(self.mainframe, font=self.FontTitle, text=f'\n{title}\n').grid(row=1, column=0, columnspan=3)
        # Make an empty Canvas
        self.snap_frame = ttk.Labelframe(self.mainframe, text='Screen View', padding=(1, 0, 1, 0))
        self.snap_frame.grid(row=10, column=0, rowspan=2, sticky=(tk.N, tk.W))
        self.screen_view = tk.Canvas(self.snap_frame, width=210, height=350, borderwidth=0)
        self.screen_view.create_rectangle(0, 0, 210, 350, fill="#FFFFFF")
        self.screen_view.create_line(0, 0, 210, 350, fill="#000000")
        self.screen_view.create_line(210, 0, 0, 350, fill="#000000")
        self.screen_view.grid(row=0, column=0, sticky=(tk.N, tk.W))

        # Controls Frame
        control_frame = ttk.Frame(self.mainframe, padding=(1, 0, 1, 0))
        control_frame.grid(row=10, column=1, rowspan=2, sticky=(tk.N, tk.W))
        # Output Frame
        output_frame = ttk.Frame(control_frame)
        output_frame.pack(expand=True, fill=tk.X, side=tk.TOP)
        # OUTDIR

        OUTDIR = ttk.Button(output_frame, text='Output', command=self.set_directory)
        createToolTip(OUTDIR, 'Set destination directory where to save screen captures.')
        OUTDIR.pack(side=tk.LEFT)
        ttk.Label(output_frame, textvar=self.OUTPUTLAB, font=self.FontInfo).pack(expand=True, fill=tk.X, side=tk.TOP)
        # Assistance Frame
        assist_frame = ttk.Frame(control_frame)
        assist_frame.pack(side=tk.LEFT)
        # Save
        self.save_this = ttk.Button(assist_frame, text='Save this..', command=self.save)
        # self.save_this = ttk.Button(assist_frame, text='Save this..')
        self.save_this.configure(state=tk.DISABLED)
        createToolTip(self.save_this, 'Save current screen capture to..')
        self.save_this.pack(side=tk.TOP, expand=0, fill=tk.X)
        # Report

        self.report_button = ttk.Button(assist_frame, textvar=self.REPCOUNT)
        self.report_button.bind('<Button-1>', self.report)
        self.report_button.configure(state=tk.DISABLED)
        createToolTip(self.report_button, 'Generate a report with created screen captures.\nNote: only works when Output is provided.')
        self.report_button.pack(side=tk.TOP, expand=0, fill=tk.X)
        # Guide
        ttk.Button(assist_frame, text='Help', command=messages.screen_guide).pack(side=tk.TOP, expand=0, fill=tk.X)
        # Note
        self.note_text = ttk.Entry(self.mainframe, width=27)
        self.note_text.configure(state=tk.DISABLED)
        self.note_text.bind("<Return>", self.capture)
        createToolTip(self.note_text, 'Type a comment press ENTER to Capture and Save.')
        # Snap
        self.snap_button = ttk.Button(self.mainframe, text='Capture', command=self.capture, takefocus=True)
        self.snap_button.grid(row=15, column=0, columnspan=1, sticky=(tk.W,))
        # Close
        ttk.Button(self.mainframe, text='Close', command=self.root.destroy)\
            .grid(row=15, column=1, columnspan=2, sticky=(tk.N, tk.E))

        self.remember_button = ttk.Checkbutton(self.mainframe, text='Remember', var=self.REMEMBER)
        createToolTip(self.remember_button, 'Keep last entered comment in field.')
        # Status
        status_frame = ttk.Frame(self.mainframe, padding=(5, 1), relief='groove')
        status_frame.grid(row=20, column=0, columnspan=3, sticky=(tk.W, tk.E))
        self.status_label = ttk.Label(status_frame, text='Ready', font=self.FontStatus)
        self.status_label.grid(row=4, column=0, sticky=tk.W, padx=5, pady=3)

    def set_directory(self):
        _path = self.get_dir()
        if _path and self.store.set_output(_path):
            self.OUTPUTLAB.set(self.store.output if len(self.store.output) < 22 else f'..{self.store.output[-20:]}')
            self.REPCOUNT.set(f'Report ({self.store.count})')
            self.report_button.configure(state=tk.NORMAL)
            self.note_text.configure(state=tk.NORMAL)
            self.note_text.grid(row=14, column=0, columnspan=1, sticky=tk.W)
            self.remember_button.grid(row=15, column=0, columnspan=1, sticky=tk.E)

    def display(self, img_obj):
        if not img_obj:
            messagebox.showwarning('Nothing to display', 'Nothing was captured. Is a device connected?')
            return None
        self.save_this.configure(state=tk.NORMAL)
        self.screen_view.grid_forget()
        img_obj.seek(0)
        head = img_obj.read(24)
        width, height = struct.unpack('>ii', head[16:24])
        factor = width // 200
        fname = os.path.realpath(img_obj.name)
        self.currentImage = tk.PhotoImage(file=fname).subsample(factor, factor)
        self.PIC = ttk.Label(self.snap_frame, image=self.currentImage)
        self.PIC.grid(row=0, column=0, sticky=(tk.N, tk.W))
        _note = self.note_text.get().rstrip()
        if _note:
            tk.Label(self.snap_frame, text=_note, font=self.FontInfo, bg='#FFFFFF').grid(row=0, column=0, sticky=(tk.S, tk.W))
            if self.REMEMBER.get() == 0:
                self.note_text.delete(0, 'end')

    @threaded
    def capture(self):
        self.status_label.configure(text='Capturing...', foreground="black")
        self.snap_button.configure(state=tk.DISABLED)
        img_obj = self.store.capture(self.note_text.get().rstrip())
        if img_obj is False:
            messagebox.showinfo('Content Protection Enabled', "It is not possible to capture this type of content.")
            self.snap_button.configure(text="Capture")
            self.snap_button.configure(state=tk.NORMAL)
            self.status_label.configure(text=messages.content_protect, foreground="blue")
        else:
            if self.store.output:
                self.REPCOUNT.set(f'Report ({self.store.count})')
            self.snap_button.configure(state=tk.NORMAL)
            self.status_label.configure(text='Ready')
            return self.display(img_obj)

    def save(self):
        file_location = self.store.items[-1][0]
        savefilename = filedialog.asksaveasfilename(
            initialdir=os.getenv('HOME') or os.getcwd(),
            initialfile=os.path.split(file_location)[1],
            filetypes=[('Portable Network Graphics', '*.png')])
        if savefilename:
            shutil.copy2(file_location, savefilename)

    @threaded
    def report(self, event=None):
        with disable_control(event):
            if not self.store.count:
                messagebox.showinfo('No Captures', "Nothing to report yet")
                return
            report = pathlib.Path(self.store.report())
            webbrowser.open_new_tab(report.as_uri())


# Preferences -----------------------------------------------------------------
class Preferences(BaseWindow):
    def __init__(self, root=None, title='User Preferences'):
        super().__init__(root=root, title=title)

        self.fields = {
            'default_path': {
                'label': 'Default OUTPUT path',
                'tooltip': 'This will be the default location path where report outputs will be saved.',
                'var': tk.StringVar,
                'control': ttk.Entry,
                'browse': True
            },
            'update_rate': {
                'label': 'Cracking update rate',
                'tooltip': 'Rate at which the UI is updated with a current value during password cracking.',
                'var': tk.IntVar,
                'control': tk.Spinbox,
                'kwargs': {'from_': 1e4, 'to': 1e6, 'increment': 1e4}
            },
            'offline_mode': {
                'label': 'Offline mode',
                'tooltip': 'Offline mode skips latest version checking on startup.',
                'var': tk.IntVar,
                'control': ttk.Checkbutton,
            },
            'save_log': {
                'label': 'Save logs',
                'tooltip': 'When OUTPUT is defined, save logs automatically',
                'var': tk.IntVar,
                'control': ttk.Checkbutton,
            },
            'window_size': {
                'label': 'Log window size',
                'tooltip': 'Log window height in line numbers',
                'var': tk.IntVar,
                'control': ttk.OptionMenu,
                'values': [12, 20],
            },
            'theme': {
                'label': 'Theme',
                'tooltip': 'Style appearance of the user interface',
                'var': tk.StringVar,
                'control': ttk.OptionMenu,
                'values': self.style_ttk.theme_names(),
            },
            'time_zone': {
                'label': 'Time zone offset',
                'tooltip': 'UTC offset for reporting time and date stamps',
                'var': tk.StringVar,
                'control': ttk.OptionMenu,
                'values': config.TIME_ZONES,
            },
            'date_format': {
                'label': 'Date format',
                'tooltip': 'Format in which the time and date are reported',
                'var': tk.StringVar,
                'control': ttk.Entry,
            },
            'custom_header': {
                'label': 'Custom header',
                'tooltip': 'Custom header information for HTML reports. Use HTML tags for customization.',
                'var': tk.StringVar,
                'control': ttk.Entry,
            },
            'custom_footer': {
                'label': 'Custom footer',
                'tooltip': 'Custom footer information for HTML reports. Use HTML tags for customization.',
                'var': tk.StringVar,
                'control': ttk.Entry,
            },
        }

        self.objects = {}
        self.render_view()

    def set_obj(self, key, var):
        obj_name = f'OBJ_{key}'
        setattr(self, obj_name, var())
        obj = getattr(self, obj_name)
        self.objects[key] = obj
        return obj

    def browse(self, event):
        with disable_control(event):
            key = event.widget.key
            value = self.get_dir(path=key)
            if value:
                self.update_obj(key, value)

    def render_view(self):
        _var = {
            ttk.Entry: 'textvar',
            tk.Spinbox: 'textvariable',
            ttk.Checkbutton: 'var',
        }
        for n, (key, values) in enumerate(self.fields.items(), start=1):
            obj = self.set_obj(key, values['var'])
            obj.set(self.conf(key))
            Control = values['control']
            args = values.get('args', [])
            kwargs = values.get('kwargs', {})
            if _var.get(Control):
                kwargs.update({_var.get(Control): obj})
            elif hasattr(Control, '_options'):
                args.extend([
                    obj,
                    self.conf(key),
                    *values.get('values', []),
                ])
            L = ttk.Label(self.mainframe, text=f"{values['label']} : ")
            createToolTip(L, values['tooltip'])
            L.grid(row=n, column=0, sticky=tk.E)
            C = Control(self.mainframe, *args, **kwargs)
            if values.get('browse'):
                C.key = key
                C.bind('<Button-1>', self.browse)
            C.grid(row=n, column=1, sticky=tk.W)
        ttk.Button(self.mainframe, text='Save', command=self.save).grid(row=n + 1, column=0, sticky=tk.E)
        ttk.Button(self.mainframe, text='Cancel', command=self.quit_app).grid(row=n + 1, column=1, sticky=tk.W)
        # ttk.Label(self.mainframe, text='Restart Andriller for changes to take effect')

    def update_obj(self, key, value):
        obj = self.objects[key]
        obj.set(value)

    def save(self):
        to_update = {}
        for key, obj in self.objects.items():
            if str(obj.get()) != self.conf(key):
                to_update[key] = obj.get()
        self.conf.update_conf(**{self.conf.NS: to_update})
        self.quit_app()


# Extra helpers ---------------------------------------------------------------
def rClicker(e):
    try:
        def rClick_Copy(e, apnd=0):
            e.widget.event_generate('<Control-c>')

        def rClick_Cut(e):
            e.widget.event_generate('<Control-x>')

        def rClick_Paste(e):
            e.widget.event_generate('<Control-v>')

        e.widget.focus()
        nclst = [
            (' Cut', lambda e=e: rClick_Cut(e)),
            (' Copy', lambda e=e: rClick_Copy(e)),
            (' Paste', lambda e=e: rClick_Paste(e)),
        ]
        rmenu = tk.Menu(None, tearoff=0, takefocus=0)
        for (txt, cmd) in nclst:
            rmenu.add_command(label=txt, command=cmd)
        rmenu.tk_popup(e.x_root + 40, e.y_root + 10, entry="0")
    except tk.TclError as e:
        logger.error(f'rClicker error: {e}')
    return "break"


# --------------------------------------------------------------------------- #


class FileHandlerError(Exception):
    pass
