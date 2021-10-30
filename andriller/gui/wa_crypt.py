import os.path
import pathlib
import tkinter as tk
from tkinter import ttk, messagebox
from .core import BaseWindow
from .. import decrypts
from .. import statics
from ..utils import threaded, human_bytes


# WhatsApp Crypt --------------------------------------------------------------
class WhatsAppCrypt(BaseWindow):
    KEY_SIZE = decrypts.WhatsAppCrypt.KEY_SIZE
    DECODED_DIR = decrypts.WhatsAppCrypt.DECODED_DIR
    DECODED_EXT = decrypts.WhatsAppCrypt.DECODED_EXT

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
            self.logger.info('WhatsAppCrypt: key file was detected & automatically selected')
            self.set_key(key=key)

    def check_dir(self):
        self.crypts.clear()
        self.file_box.delete(*self.file_box.get_children())
        path_ = pathlib.Path(self.work_dir)
        for f in path_.glob('*.crypt*'):
            done = f.parent.joinpath(self.DECODED_DIR, f'{f.name}{self.DECODED_EXT}').exists()
            size = human_bytes(os.path.getsize(f))
            item = self.file_box.insert('', tk.END, text=f.name, values=[size, done])
            self.crypts[item] = str(f)

    def tree_update(self, iid, values):
        self.file_box.item(iid, values=values)

    def decrypt_all(self):
        self.file_box.selection_add(self.file_box.get_children())
        self.decrypt_sel()

    def decrypt_sel(self):
        sel = self.file_box.selection()
        if not sel:
            messagebox.showwarning('No selection made', 'Select at least one database to decrypt.')
            return
        self.run_decrypt(sel)

    @threaded
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
                        wadec = decrypter(
                            pathlib.Path(file_),
                            pathlib.Path(self.key_file)
                        )
                        if wadec.decrypt():
                            vals = self.file_box.item(i)['values']
                            vals[1] = True
                            self.file_box.item(i, values=vals, tags='success')
                            self.logger.info(f'WhatsAppCrypt: {fname} successfully decrypted.')
                    except decrypts.WhatsAppCryptError as err:
                        self.logger.error(f'WhatsAppCrypt: {err}')
                        self.file_box.item(i, tags='failure')
                        messagebox.showerror('WhatsApp decryption error', str(err))
                    except Exception as err:
                        self.logger.exception(f'WhatsAppCrypt: {fname}: {err}')
                        self.file_box.item(i, tags='failure')
        finally:
            self.file_box.selection_set()
            self.controls_state(tk.NORMAL)

    def get_supported(self):
        return {kls.CRYPT: kls for kls in decrypts.WhatsAppCrypt.__subclasses__()}
