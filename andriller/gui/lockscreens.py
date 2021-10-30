import json
import string
import os.path
import binascii
import itertools
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .. import decoders
from .. import cracking
from ..utils import threaded
from ..exceptions import FileHandlerError
from .core import BaseWindow, rClicker
from .tooltips import createToolTip


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
                self.logger.warning(f'{e}')
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
    def __init__(self, root=None, title=None):
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
                self.logger.info(f'Lockscreen salt: {salt_value}')
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
                    self.logger.info(f'Lockscreen salt: {salt_value}')
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
                self.logger.info(f'Lockscreen salt: {salt_values[0]}')
                self.SALT.set(salt_values[0])
            elif len(salt_values) > 1:
                for n, s in enumerate(salt_values, start=1):
                    self.logger.info(f'Lockscreen salt_{n}: {s}')
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
                    self.logger.info(f'Password hash: {hash_val}')
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
                self.logger.info(f'Lockscreen credential found: {result}')
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
