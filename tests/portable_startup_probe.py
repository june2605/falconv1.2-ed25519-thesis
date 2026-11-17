"""External negative tests of copied frozen files; never edit the real release."""
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

Probe = runpy.run_path(str(Path(__file__).with_name('portable_probe.py')))['Probe']

if __name__ == '__main__':
    source, workspace, evidence = (Path(v).resolve() for v in sys.argv[1:4])
    results = []
    for case, expected in [('assets', 'Bundled application assets'), ('metadata', 'Bundled runtime metadata'),
                           ('version', 'Bundled runtime version')]:
        destination = workspace / ('Startup negative ' + case)
        def omitted(directory, names):
            if Path(directory).name != '_internal': return []
            return ['frontend'] if case == 'assets' else ['pywebview-6.2.1.dist-info'] if case == 'metadata' else []
        shutil.copytree(source, destination, ignore=omitted)
        if case == 'version':
            path = destination / '_internal/pywebview-6.2.1.dist-info/METADATA'
            data = path.read_bytes(); assert data.count(b'Version: 6.2.1\n') == 1
            path.write_bytes(data.replace(b'Version: 6.2.1\n', b'Version: 0.0.0\n', 1))
        probe = Probe(destination, workspace, evidence)
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
        env['PATH'] = os.environ['WINDIR'] + '\\System32;' + os.environ['WINDIR']
        probe.process = subprocess.Popen([str(destination / 'HybridSign.exe')], cwd=workspace, env=env)
        dialog = probe.wait(lambda: probe.modal('Startup error'))
        text = ' '.join(n.Current.Name for n in probe.nodes(dialog))
        assert expected in text and 'complete portable distribution' in text and 'Traceback' not in text
        assert not any(w.Current.Name == 'HybridSign \u2014 Desktop Preview' for w in probe.windows())
        probe.window = dialog
        probe.capture('startup-' + case + '.png')
        probe.click('OK', root=dialog)
        assert probe.process.wait(timeout=20) == 1
        results.append({'case': case, 'passed': True, 'nativeErrorShown': True, 'exitCode': 1})
    (evidence / 'startup-checks.json').write_text(json.dumps({'passed': True, 'cases': results}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, 'cases': results}))
