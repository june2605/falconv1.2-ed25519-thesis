"""Run the Windows release checks sequentially and retain each runner's result."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=1, help='Number of complete Python then Playwright rounds')
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('--rounds must be at least one')

    root = Path(__file__).resolve().parents[1]
    work = root / 'tmp'
    work.mkdir(exist_ok=True)
    logs = Path(tempfile.mkdtemp(prefix='release-regression-', dir=work))
    print(f'Release logs: {logs}', flush=True)
    results = {}

    def run(name, command, cwd):
        log = logs / (name + '.txt')
        print(f'Starting {name}', flush=True)
        with log.open('wb') as output:
            process = subprocess.run(command, cwd=cwd, stdout=output, stderr=output)
        results[name] = process.returncode
        (logs / 'exit-codes.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
        print(f'{name} exited {process.returncode}. Log: {log.name}', flush=True)
        return process.returncode

    frontend = root / 'frontend'
    run('typecheck', ['npm.cmd', 'run', 'typecheck'], frontend)
    if run('build', ['npm.cmd', 'run', 'build'], frontend):
        return 1  # The native and browser suites require the freshly built app.
    for index in range(1, args.rounds + 1):
        run(f'python-{index}', [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], root)
        run(f'playwright-{index}', ['npm.cmd', 'run', 'test:e2e'], frontend)
    return int(any(results.values()))


if __name__ == '__main__':
    raise SystemExit(main())
