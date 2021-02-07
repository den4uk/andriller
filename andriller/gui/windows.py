#!/usr/bin/env python3

import sys
import os.path
import pathlib
import logging
import datetime
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .. import __version__, __app_name__
from .. import driller
from .. import adb_conn
from .. import decoders
from .. import messages
from ..utils import threaded, DrillerTools
from .core import (
    BaseWindow,
    rClicker,
    disable_control,
    log_errors,
)
from .tooltips import createToolTip
from .preferences import Preferences
from .screen_cap import ScreenCap
from .wa_crypt import WhatsAppCrypt
from .lockscreens import (
    BrutePattern,
    BruteGenPin,
    BruteGenDict,
    BruteSamDict,
    BruteSamPin,
    BruteForceGen,
)


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
            # with contextlib.suppress(Exception):
            self.handleError(record)


# Main Window -----------------------------------------------------------------
class MainWindow(BaseWindow):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title()
        self.adb = adb_conn.ADBConn()
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
            height=self.conf('window_size'))
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
        self.logger.info(f'Started: {__app_name__} {__version__}')
        self.logger.info(f"Time settings/format: {self.conf('date_format')}")
        self.logger.info(f"Detected/PC time: {self.time_now_local}")
        self.logger.info(f"Universal time:   {self.time_now_utc}")
        self.logger.info(f"Time in reports:  {self.time_now_configured} <--")  # \u2190
        self.conf.check_latest_version(logger=self.logger)

        # Setup ADB logging
        # do not pass self.logger as the logger, as the logger's lifetime is shorter, and is not reliable.
        self.adb.setup_logging(log_level=self.log_level)

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
        self.logger.addHandler(log_handler)

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
        if not getattr(sys, 'frozen', False):
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
            self.logger.info(f'Converting {ab_file}')
            self.StatusMsg.set('Converting to tar...')
            tar_ = DrillerTools.ab_to_tar(ab_file, to_tmp=False)
            self.logger.info(f'Converted to: {tar_}')
            self.StatusMsg.set('Finished')

    @threaded
    def ab_to_folder(self):
        ab_file = self.get_file('', ftype=[('AB File', '*.ab')])
        if ab_file:
            self.logger.info(f'Converting {ab_file}')
            self.StatusMsg.set('Converting to tar...')
            tar_ = DrillerTools.ab_to_tar(ab_file, to_tmp=False)
            self.StatusMsg.set('Extracting tar members...')
            dst_ = pathlib.Path(f'{ab_file}_extracted/')
            dst_.mkdir()
            for _ in DrillerTools.extract_form_tar(tar_, dst_, full=True):
                pass
            self.logger.info(f'Extracted to: {dst_}')
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
            self.logger.info(f'Decoding: {os.path.basename(file_path)}')
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
                    logger=self.logger)
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
                        logger=self.logger)
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
                        logger=self.logger)
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
                        logger=self.logger)
                    drill.CreateWorkDir()
                    drill.ExtractFromDir()
                    drill.DataDecoding()
                    drill.GenerateHtmlReport()
                    drill.GenerateXlsxReport()
                    drill.CleanUp()
