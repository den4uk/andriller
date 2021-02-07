import struct
import shutil
import pathlib
import os.path
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .. import __app_name__
from .. import screencap
from .. import messages
from ..utils import threaded
from .core import BaseWindow, disable_control
from .tooltips import createToolTip


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
