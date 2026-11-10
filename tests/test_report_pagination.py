"""Exercise the actual browser pagination controller with a minimal DOM boundary."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from report_pagination import REPORT_PAGINATION_JS


class ReportPaginationTests(unittest.TestCase):
    def test_activation_scrolling_filtering_and_removal_keep_exact_batches(self):
        # No rendering engine is needed: only the container insertion boundary is replaced.
        script = r"""
const assert = require('node:assert/strict');
global.window = {};
let intersection;
global.IntersectionObserver = window.IntersectionObserver = class {
  constructor(callback) { intersection = callback; }
  observe() {}
};
const container = {children: [], insertBefore(node, before) {
  node.remove();
  const index = before ? this.children.indexOf(before) : this.children.length;
  this.children.splice(index, 0, node); node.parent = this;
}};
const records = Array.from({length: 25}, (_, id) => ({id, parent:null, querySelectorAll:()=>[], remove() {
  if (this.parent) this.parent.children.splice(this.parent.children.indexOf(this),1);
  this.parent = null;
}}));
let click;
const button = {hidden:false,addEventListener(name,callback){click=callback;}};
const count = {textContent:''};
const panel = {hidden:true,querySelector(selector){return selector==='button' ? button : count;}};
const page = {hidden:true};
const mounted = new Set();
const list = new ReportPagedList(container,panel,page,node=>mounted.add(node.id));
list.setItems(records);
assert.equal(container.children.length,0,'Inactive pages must not mount cards');
page.hidden=false; list.activate();
assert.deepEqual(container.children.map(node=>node.id),[0,1,2,3,4,5,6,7,8,9]);
intersection([{isIntersecting:true}]);
assert.equal(container.children.length,20,'Scrolling should add exactly one batch');
page.hidden=true; intersection([{isIntersecting:true}]);
assert.equal(container.children.length,20,'Hidden pages must not preload more cards');
page.hidden=false; click();
assert.equal(container.children.length,25);
assert.equal(button.hidden,true);
list.setItems(records.slice(12));
assert.deepEqual(container.children.map(node=>node.id),[12,13,14,15,16,17,18,19,20,21]);
assert.equal(button.hidden,false);
assert.match(count.textContent,/10.*13/);
click(); assert.equal(container.children.length,13);
list.setItems(records.slice(13),false);
assert.equal(container.children.length,12,'Removing an unloaded/loaded entry must not leave stale cards');
list.setItems([]);
assert.equal(container.children.length,0);
assert.equal(panel.hidden,true);
"""
        result = subprocess.run(['node', '-'], input=REPORT_PAGINATION_JS + '\n' + script, text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_filtered_bulk_scope_includes_records_beyond_the_mounted_batch(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts/generate_html_report.py').read_text(encoding='utf-8')
        start = source.index('    function visibleMusicPaths()')
        end = source.index('    function singleMusicPath', start)
        function = source[start:end].replace('{{', '{').replace('}}', '}')
        script = "const assert=require('node:assert/strict'); const musicCards=Array.from({length:25},(_,i)=>({hidden:i===23,dataset:{filePath:'track-'+i},isConnected:i<10}));\n" + function + "\nassert.equal(visibleMusicPaths().length,24); assert.ok(visibleMusicPaths().includes('track-24')); assert.ok(!visibleMusicPaths().includes('track-23'));"
        result = subprocess.run(['node','-'], input=script,text=True,encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
