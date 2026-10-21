"""Observer is evaluated with a fake V2 context, never loaded into a running CLI."""
import subprocess
from pathlib import Path

from test_opencode_v2_control_plane import project

ROOT = Path(__file__).resolve().parents[1]
OBSERVER = ROOT / 'private_dot_config/dotfiles-ai/opencode-maintenance-observer/observer.mjs'


def test_observer_reads_exact_route_without_prompt_or_network(tmp_path):
    script = tmp_path / 'test.mjs'
    script.write_text('''import { sample } from %s;
import assert from 'node:assert/strict';
const context = {
 app: { version: '2.1.2' },
 ui: { router: { current: () => ({type:'session', sessionID:'ses_child', prompt:'secret'}) },
       tabs: {enabled: () => true, list: () => [{sessionID:'ses_root', active:true, title:'secret'}]} },
 data: {session: {get: id => ({id, location:{directory:'/fixture/repository'}, title:'secret'})}},
};
let record = sample(context, null);
assert.equal(record.viewed_session_id, 'ses_child');
assert.equal(record.session_directory, '/fixture/repository');
assert.equal(JSON.stringify(record).includes('secret'), false);
context.ui.router.current = () => ({type:'home'});
record = sample(context, record.last_viewed_session_id);
assert.equal(record.viewed_session_id, null);
assert.equal(record.last_viewed_session_id, 'ses_child');
context.ui.router.current = () => ({type:'session', sessionID:'invalid'});
assert.throws(() => sample(context, null));
''' % repr(str(OBSERVER)))
    result = subprocess.run(['bun', str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_plugin_merge_preserves_unrelated_plugins(tmp_path):
    import json
    path = tmp_path / '.config/opencode/cli.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'plugins': [{'package': 'fixture-plugin', 'options': {'local': True}}, '*', '-opencode.notifications']}))
    rendered = project(tmp_path, 'cli.json')
    assert rendered['plugins'][0] == {'package': 'fixture-plugin', 'options': {'local': True}}
    assert rendered['plugins'][1:3] == ['*', '-opencode.notifications']
    assert rendered['plugins'][3]['package'].endswith('/dotfiles-ai/opencode-maintenance-observer')
    assert project(tmp_path, 'cli.json') == rendered


def test_observer_atomic_private_storage_cleanup_and_incarnations(tmp_path):
    import json
    import socket
    import tempfile
    with tempfile.TemporaryDirectory(prefix='observer-', dir='/private/tmp') as directory:
        root = Path(directory)
        (root / '.dotfiles-ai-state').write_text('fixture')
        (root / 'herdr').mkdir(mode=0o700)
        backend = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        backend.bind(str(root / 'backend.sock'))
        try:
            script = tmp_path / 'storage.mjs'
            script.write_text('''import { startObserver } from %s;
import fs from 'node:fs';
import assert from 'node:assert/strict';
const root = %s;
const environment = {HERDR_ENV:'1', HERDR_PANE_ID:'w1:p1', HERDR_SOCKET_PATH:root+'/backend.sock', DOTFILES_AI_STATE_ROOT:root};
const context = {app:{version:'2.1.2'}, ui:{router:{current:()=>({type:'session',sessionID:'ses_child'})}, tabs:{enabled:()=>false}}, data:{session:{get:id=>({id, location:{directory:'/fixture/repository'}})}}};
const stop = startObserver(context, environment);
stop();
const stopAgain = startObserver(context, environment);
stopAgain();
const folder = root+'/herdr/opencode-observers';
const files = fs.readdirSync(folder);
assert.equal(files.length, 2);
assert.ok(files.every(name => name.endsWith('.json')));
const records = files.map(name => {
  assert.equal(fs.statSync(folder+'/'+name).mode & 0o777, 0o600);
  return JSON.parse(fs.readFileSync(folder+'/'+name));
});
assert.notEqual(records[0].incarnation, records[1].incarnation);
assert.ok(records.every(record => record.viewed_session_id === 'ses_child'));
await new Promise(resolve => setTimeout(resolve, 600));
assert.equal(fs.readdirSync(folder).length, 2);
// Invalid root disables itself and leaves the running context alone.
startObserver(context, {...environment, DOTFILES_AI_STATE_ROOT:root+'/absent'})();
assert.equal(fs.existsSync(root+'/absent'), false);
''' % (repr(str(OBSERVER)), json.dumps(str(root))))
            result = subprocess.run(['bun', str(script)], capture_output=True, text=True, timeout=5)
            assert result.returncode == 0, result.stderr
        finally:
            backend.close()
