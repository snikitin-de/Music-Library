import subprocess
import unittest
from pathlib import Path


class ReportModeTests(unittest.TestCase):
    def test_sidebar_toggle_cycles_modes_and_keeps_confirmation_visible(self):
        source=(Path(__file__).resolve().parents[1]/'scripts/generate_html_report.py').read_text(encoding='utf-8')
        start=source.index('    function selectedMode()')
        end=source.index('    function visibleMusicPaths()',start)
        functions=source[start:end].replace('{{','{').replace('}}','}')
        script=r"""
const assert=require('node:assert/strict');
const classes=new Set();
const processingModeNote={dataset:{mode:'dry-run'},attributes:{},setAttribute(name,value){this.attributes[name]=value;},classList:{add(name){classes.add(name);},remove(name){classes.delete(name);}}};
const processingModeTitle={textContent:''}, processingModeDetail={textContent:''}, operationStatus={textContent:''};
"""+functions+r"""
updateOperationStatus();
assert.equal(selectedMode(),'dry-run');
assert.equal(processingModeNote.attributes['aria-pressed'],'false');
toggleProcessingMode();
assert.equal(selectedMode(),'real');
assert.equal(processingModeNote.attributes['aria-pressed'],'true');
assert.equal(processingModeTitle.textContent,'Применить изменения');
assert.match(processingModeDetail.textContent,/подтверждения/);
assert.equal(operationStatus.textContent,'');
assert.ok(classes.has('mode-real'));
toggleProcessingMode();
assert.equal(selectedMode(),'dry-run');
assert.equal(processingModeTitle.textContent,'Режим проверки');
assert.equal(processingModeNote.attributes['aria-pressed'],'false');
assert.ok(!classes.has('mode-real'));
toggleProcessingMode();
assert.equal(selectedMode(),'real');
"""
        result=subprocess.run(['node','-'],input=script,text=True,encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
