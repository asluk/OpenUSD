"""Run full-proposal readiness and the independently derivable discovery controls."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pxr import Usd
from geobuild.quality import assessment, require_derivable_proposal, ProposalNotReady
from review.fixtures import build
from review.scope import queries


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(arguments, log, env=None, timeout=300):
    with Path(log).open('w', encoding='utf-8') as stream:
        process = subprocess.run(arguments, stdout=stream, stderr=subprocess.STDOUT, env=env, timeout=timeout)
    if process.returncode:
        raise RuntimeError('Independent control failed; inspect ' + Path(log).name)


def execute(root, args):
    root = Path(root)
    output = Path(args.output).resolve()
    if output.exists():
        raise RuntimeError('Use a fresh output directory; previous receipts are immutable')
    output.mkdir(parents=True)
    delivery = output/'delivery'
    delivery.mkdir()
    inputs = json.loads((root/'inputs.json').read_text())
    assert sha(root/'proposal/proposal-source.txt') == inputs['proposal']['sha256']
    for name, expected in inputs['derivation'].items():
        assert sha(root/'proposal'/name) == expected, 'Derivation changed after freeze: ' + name
    completion = assessment(root)
    try:
        require_derivable_proposal(root)
    except ProposalNotReady as error:
        stopping_reason = str(error)
    else:
        raise RuntimeError('This limited control runner is not a complete placement build')
    completion.update(experimental_execution_authorized=False, placement_execution_stopped=True)
    jobs = build(root, output/'scope-fixtures')
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root)
    command([sys.executable, '-X', 'utf8', '-m', 'pytest', str(root/'review/test_contracts.py'), '-q',
             '--junitxml=' + str(output/'contracts.xml')], output/'contracts.log', env)
    cases = ET.parse(output/'contracts.xml').getroot().findall('.//testcase')
    assert not any(case.findall('failure') or case.findall('error') for case in cases)
    headless = []
    source_file_hashes = {p.name: sha(p) for p in (output/'scope-fixtures').glob('*.usda')}
    for job in jobs:
        stage = Usd.Stage.Open(job['stage'], load=Usd.Stage.LoadNone if job['load_none'] else Usd.Stage.LoadAll)
        result = queries(stage, job['queries'])
        assert result['queries'] == job['expected'], job['name']
        headless.append({'name': job['name'], **result})
    (output/'scope-jobs.json').write_text(json.dumps(jobs, indent=2) + '\n')
    if not all([args.native_build, args.usd_sdk, args.native_python, args.ov_sdk]):
        raise RuntimeError('Native USD and live OV paths are required for the selected discovery controls')
    command([args.cmake, '-S', str(root/'native'), '-B', args.native_build], output/'scope-native-configure.log')
    command([args.cmake, '--build', args.native_build, '--target', 'proposalScope'], output/'scope-native-build.log')
    native_env = env.copy()
    native_env['PATH'] = ';'.join([str(Path(args.usd_sdk)/'bin'), str(Path(args.usd_sdk)/'lib'), args.native_python, env.get('PATH', '')])
    native_exe = Path(args.native_build)/'proposalScope.exe'
    command([str(native_exe), str(output/'scope-jobs.json'), str(output/'scope-native.json')], output/'scope-native.log', native_env)
    ov_env = env.copy()
    ov_env.update(GEOBUILD_OV_SDK=args.ov_sdk, GEOBUILD_SCOPE_JOBS=str(output/'scope-jobs.json'),
                  GEOBUILD_SCOPE_RESULT=str(output/'scope-ov.json'), GEOBUILD_SCOPE_ERROR=str(output/'scope-ov-error.txt'),
                  PYTHONNOUSERSITE='1')
    command([str(Path(args.ov_sdk)/'python/python.exe'), '-s', str(root/'review/ov_scope_launch.py')], output/'scope-ov.log', ov_env)
    if (output/'scope-ov-error.txt').exists():
        raise RuntimeError('Live OV scope control failed; inspect scope-ov-error.txt')
    native = json.loads((output/'scope-native.json').read_text())
    ov = json.loads((output/'scope-ov.json').read_text())
    for results in [native, ov]:
        assert len(results) == len(jobs)
        for result, job in zip(results, jobs):
            assert result['name'] == job['name'] and result['queries'] == job['expected']
            assert result['source_unchanged']
    assert source_file_hashes == {p.name: sha(p) for p in (output/'scope-fixtures').glob('*.usda')}
    rows = []
    for job in jobs:
        rows.append({'name': job['name'], 'queries': len(job['queries']),
                     'successful_definition_queries': sum(x['success'] for x in job['expected']),
                     'expected_failures': sum(not x['success'] for x in job['expected']),
                     'headless': 'passed', 'native_usd': 'passed', 'live_ov': 'passed'})
    source_files = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*')
                    if p.is_file() and p.suffix in ['.py', '.cpp', '.h', '.md', '.json', '.txt', '.kit', '.usda']
                    and p.name != 'README.md' and not any(x in p.parts for x in ['delivery', 'collateral', '__pycache__', '.pytest_cache'])}
    report = {
        'status': 'placement derivation stopped; shared CRS discovery controls executed',
        'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
        'inputs': inputs, 'source_files': source_files, 'completion': completion,
        'stopping_reason': stopping_reason,
        'proposal_quality': json.loads((root/'proposal-quality.json').read_text()),
        'tests': {'passed': len(cases), 'failed': 0}, 'scope_controls': rows,
        'scope_queries_per_reader': sum(x['queries'] for x in rows),
        'discovery_readers': ['headless OpenUSD', 'native OpenUSD', 'live OV stage'],
        'native_executable_sha256': sha(native_exe),
        'placement_runtime_jobs': 0, 'hydra_placement_jobs': 0, 'ov_placement_jobs': 0,
        'exports': [], 'geodetic_accuracy_claim': False, 'source_files_unchanged': True,
        'limitations': [
            'This run verifies CRS discovery, composition, definition property types and source preservation; it does not certify the unspecified WKT normal form.',
            'Native USD discovery is not Hydra placement or rendering. Live OV discovery is not resolved geometry ingestion.',
            'Missing placement, component, adjustment, measurement, declaration, result and export definitions stop dependent derivation.',
            'The retained earlier relationship-based experiment is incompatible with the shared binding format and was not rerun or silently adopted.',
            'No previous numerical result, image, export or deck is relabeled as newly executed evidence.'
        ]}
    for name in ['proposal-quality.json']:
        (delivery/name).write_bytes((root/name).read_bytes())
    (delivery/'run-report.json').write_text(json.dumps(report, indent=2) + '\n')
    (delivery/'scope-results.json').write_text(json.dumps({'headless': headless, 'native_usd': native, 'live_ov': ov}, indent=2) + '\n')
    print(json.dumps({'proposal_ready': False, 'tests': len(cases), 'scope_cases': len(rows),
                      'scope_queries_per_reader': report['scope_queries_per_reader'], 'delivery': str(delivery)}, indent=2))
    return 2
