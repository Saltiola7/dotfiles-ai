"""Credential-free project enumeration uses only synthetic, isolated cache state."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from test_opencode_control_plane import ROOT

MODULE = ROOT / 'dot_agents/skills/jfrog-init/scripts/lib/project-cache.mjs'
CREDENTIALS = {'baseUrl': 'https://fixture.invalid', 'token': 'fixture-token',
               'user': 'fixture-user', 'password': 'fixture-password'}
BODY = [{'project_key': 'fixture', 'display_name': 'Fixture project'}]


def run_cache(tmp_path, body):
    node = shutil.which('node')
    assert node, 'project-selected Node is required for the cache regression'
    source = (f'import * as cache from {json.dumps(MODULE.as_uri())};\n'
              'import { readdirSync } from "node:fs";\n'
              f'const creds = {json.dumps(CREDENTIALS)};\n' + body)
    environment = {'HOME': str(tmp_path), 'TMPDIR': str(tmp_path), 'TMP': str(tmp_path),
                   'TEMP': str(tmp_path), 'PATH': os.defpath, 'LANG': 'C', 'LC_ALL': 'C'}
    result = subprocess.run([node, '--input-type=module', '-e', source],
                            cwd=tmp_path, env=environment, capture_output=True,
                            text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_cache_write_retains_no_project_or_credential_material(tmp_path):
    result = run_cache(tmp_path,
        f'cache.writeCachedProjectList("fixture", creds, {json.dumps(BODY)});\n'
        'console.log(JSON.stringify({read:cache.readCachedProjectList("fixture",creds),'
        'files:readdirSync(process.env.TMPDIR)}));')
    assert result == {'read': None, 'files': []}


def test_legacy_cache_is_ignored_without_modifying_it(tmp_path):
    # Precomputed fingerprint belongs only to the fixed synthetic fixture above.
    legacy = tmp_path / 'jfrog-init-projects-fixture.json'
    legacy.write_text(json.dumps({'fetchedAt': int(time.time() * 1000),
                                 'fingerprint': '59f52b29502d7c47', 'body': BODY}))
    before = legacy.read_bytes()
    result = run_cache(tmp_path,
        'console.log(JSON.stringify({read:cache.readCachedProjectList("fixture",creds)}));')
    assert result == {'read': None}
    assert legacy.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == [legacy.name]


def test_cache_helpers_never_inspect_credential_properties(tmp_path):
    result = run_cache(tmp_path, '''
let accesses = 0;
const guarded = {};
for (const key of Object.keys(creds)) {
  Object.defineProperty(guarded, key, {get() { accesses++; return creds[key]; }});
}
cache.writeCachedProjectList("fixture", guarded, []);
cache.readCachedProjectList("fixture", guarded);
console.log(JSON.stringify({accesses,files:readdirSync(process.env.TMPDIR)}));
''')
    assert result == {'accesses': 0, 'files': []}
