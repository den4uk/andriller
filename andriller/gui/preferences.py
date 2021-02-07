import tkinter as tk
from tkinter import ttk
from .. import config
from .core import BaseWindow, disable_control
from .tooltips import createToolTip


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
