import os
import tempfile
from andriller import driller


def test_parse_dir():
    with tempfile.TemporaryDirectory() as fake_home:
        os.environ['HOME'] = fake_home
        base_dir = tempfile.TemporaryDirectory()
        src_dir = os.path.join(os.path.dirname(__file__), 'data')
        assert 'data' in os.listdir(src_dir)
        assert 'com.android.providers.contacts' in os.listdir(os.path.join(src_dir, 'data'))
        drill = driller.ChainExecution(base_dir.name, src_dir=src_dir)
        drill.CreateWorkDir()
        assert len(os.listdir(base_dir.name)) == 1
        assert os.listdir(base_dir.name)[0].startswith('andriller_') is True
        drill.ExtractFromDir()
        assert len(drill.DOWNLOADS) > 0
        drill.DataDecoding()
        assert len(drill.DECODED) > 0
        drill.GenerateHtmlReport(open_html=False)
        drill.GenerateXlsxReport()
        drill.CleanUp()
        assert os.path.exists(drill.output_dir)
        _dir = os.path.join(base_dir.name, os.listdir(base_dir.name)[0])
        _dir_cont = os.listdir(_dir)
        assert 'REPORT.html' in _dir_cont
        assert 'REPORT.xlsx' in _dir_cont
        assert 'DataStore.tar' in _dir_cont
        assert 'data' in _dir_cont
