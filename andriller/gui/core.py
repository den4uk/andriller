import sys
import os.path
import logging
import functools
import contextlib
import tkinter as tk
from tkinter import ttk, font, filedialog
from .. import __app_name__
from .. import config
from .. import messages
from ..exceptions import FileHandlerError
from ..utils import threaded

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def disable_control(event, *args, **kwargs):
    try:
        event.widget.config(state=tk.DISABLED)
        yield
    finally:
        event.widget.config(state=tk.NORMAL)


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
        self.logger = kwargs.get('logger', logger)
        self.logger.setLevel(self.log_level)
        if root:
            self.root = tk.Toplevel(root, takefocus=True)
            self.root.protocol("WM_TAKE_FOCUS")
            self.root.transient(root)
            self.root.bind('<Escape>', lambda e: self.root.destroy)
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
        if isinstance(self.root, tk.Tk):
            self.root.mainloop()
        else:
            self.root.wait_window()

    def quit_app(self, event=None):
        self.root.withdraw()
        self.root.destroy()
        if isinstance(self.root, tk.Tk):
            self.root.quit()

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
