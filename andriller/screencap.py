#!/usr/bin/env python3

import os
import re
import shutil
import tempfile
import threading
from . import engines
from . import adb_conn


class ScreenStore:
    def __init__(self):
        self.output = None
        self.items = []
        self.adb = adb_conn.ADBConn()
        self.jenv = engines.get_engine()
        self.template_name = 'ScreencapReport.html'
        self.start_adb()

    @property
    def count(self):
        return len(self.items)

    @property
    def report_file(self):
        if self.output:
            return os.path.join(self.output, self.template_name)

    def start_adb(self):
        threading.Thread(target=self.adb.start).start()

    def set_output(self, path):
        if path and os.path.isdir(path):
            self.output = os.path.realpath(os.path.join(path))
            return self.output

    def save(self, img_obj):
        if self.output:
            img_path = os.path.join(self.output, os.path.split(img_obj.name)[1])
            shutil.copy2(img_obj.name, img_path)
            return img_path
        return img_obj.name

    def capture(self, note=None):
        serial = self.adb.device()[0]
        if not serial:
            return None
        tmp_img = tempfile.NamedTemporaryFile(delete=False, prefix=f'{serial}_', suffix='.png')
        raw_cap = self.adb.adb('exec-out screencap -p', binary=True)
        if not raw_cap or set(raw_cap) == {0}:
            return False
        elif isinstance(raw_cap, bytes) and re.match(b'\x89PNG', raw_cap):
            tmp_img.write(raw_cap)
            tmp_img.flush()
            tmp_img.seek(0)
            img_path = self.save(tmp_img)
            self.items.append([img_path, note])
            return tmp_img

    def hoover(self):
        for n, (item, _) in enumerate(self.items):
            directory, file_name = os.path.split(item)
            if directory != self.output:
                dst = os.path.join(self.output, file_name)
                self.items[n][0] = dst
                shutil.copy2(item, dst)

    def report(self):
        self.hoover()
        template = self.jenv.get_template(self.template_name)
        with open(self.report_file, 'w') as W:
            W.write(template.render(items=self.items, **engines.get_head_foot()))
        return self.report_file
