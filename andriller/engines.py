import os
import re
import jinja2
import xlsxwriter
from . import config

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@jinja2.evalcontextfilter
def nl2br(eval_ctx, value):
    result = '\n\n'.join(
        "<p>{0}</p>".format(p.replace('\n', jinja2.Markup('<br>\n')))
        for p in _paragraph_re.split(jinja2.escape(value)))
    if eval_ctx.autoescape:
        result = jinja2.Markup(result)
    return result


def get_engine():
    file_loader = jinja2.FileSystemLoader(os.path.join(config.CODEPATH, 'templates'))
    engine = jinja2.Environment(loader=file_loader)
    engine.filters['nl2br'] = nl2br
    return engine


class Workbook:
    EXT = 'xlsx'

    def __init__(self, work_dir, name):
        params = {'strings_to_urls': False, 'strings_to_formulas': False}
        self.header = {'bold': True, 'bg_color': "#72A0C1"}
        self.file_name = f'{name}.{self.EXT}'
        self.work_dir = work_dir
        self.file_path = os.path.join(self.work_dir, self.file_name)
        self.workbook = xlsxwriter.Workbook(self.file_path, params)

    def add_sheet(self, sheet):
        return self.workbook.add_worksheet(sheet)

    def write_header(self, sheet, titles, row=0, col=0):
        sheet.write_row(row, col, titles, self.workbook.add_format(self.header))

    def close(self):
        self.workbook.close()


def get_head_foot():
    c = config.Config()
    fields = ['custom_header', 'custom_footer']
    return {_: c(_) for _ in fields}
