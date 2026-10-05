"""Run full-proposal readiness and the independently derivable discovery controls."""
from pathlib import Path
import datetime
import hashlib
import json
import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pxr import Usd
from geobuild.quality import assessment, require_derivable_proposal, ProposalNotReady
from review.fixtures import build
from review.scope import queries
from review.origin_queries import queries as origin_queries
from review.placement_values import queries as placement_queries


def assert_results(actual, expected):
    """Exact structure/text; a priori 2e-14 component allowance for source slerp."""
    if isinstance(expected, dict):
        assert set(actual) == set(expected), (actual, expected)
        for key in expected:
            assert_results(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected):
            assert_results(left, right)
    elif isinstance(expected, float):
        assert math.isfinite(actual) and abs(actual - expected) <= 2e-14, (actual, expected)
    else:
        assert actual == expected, (actual, expected)


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
    command([sys.executable, '-X', 'utf8', '-m', 'pytest', str(root/'review/test_contracts.py'), str(root/'review/test_wkt_contracts.py'), '-q',
             '--junitxml=' + str(output/'contracts.xml')], output/'contracts.log', env)
    cases = ET.parse(output/'contracts.xml').getroot().findall('.//testcase')
    assert not any(case.findall('failure') or case.findall('error') for case in cases)
    headless = []
    source_file_hashes = {p.name: sha(p) for p in (output/'scope-fixtures').glob('*.usda')}
    for job in jobs:
        stage = Usd.Stage.Open(job['stage'], load=Usd.Stage.LoadNone if job['load_none'] else Usd.Stage.LoadAll)
        result = (origin_queries(stage, job['queries'], job['output_wkt'], job['time'], job['interpolation'])
                  if job.get('kind') == 'origin_coordinates' else placement_queries(stage, job['queries'], job['time'], job['interpolation'])
                  if job.get('kind') == 'placement_values' else queries(stage, job['queries']))
        check_job(result, job)
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
                  GEOBUILD_PYTHON_DEPENDENCIES=args.python_dependencies, PYTHONNOUSERSITE='1')
    command([str(Path(args.ov_sdk)/'python/python.exe'), '-s', str(root/'review/ov_scope_launch.py')], output/'scope-ov.log', ov_env)
    if (output/'scope-ov-error.txt').exists():
        raise RuntimeError('Live OV scope control failed; inspect scope-ov-error.txt')
    native = json.loads((output/'scope-native.json').read_text())
    ov = json.loads((output/'scope-ov.json').read_text())
    for results in [native, ov]:
        assert len(results) == len(jobs)
        for result, job in zip(results, jobs):
            assert result['name'] == job['name']
            check_job(result, job)
            assert result['source_unchanged']
    assert source_file_hashes == {p.name: sha(p) for p in (output/'scope-fixtures').glob('*.usda')}
    origin_metrics = origin_agreement(jobs, headless, native, ov)
    rows = []
    for job in jobs:
        rows.append({'name': job['name'], 'kind': job.get('kind', 'discovery'), 'queries': len(job['queries']),
                     'successful_definition_queries': sum(x['success'] for x in job['expected']),
                     'expected_failures': sum(not x['success'] for x in job['expected']),
                     'headless': 'passed', 'native_usd': 'passed', 'live_ov': 'passed'})
    source_files = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*')
                    if p.is_file() and p.suffix in ['.py', '.cpp', '.h', '.md', '.json', '.txt', '.kit', '.usda']
                    and p.name != 'README.md' and not any(x in p.parts for x in ['delivery', 'collateral', '__pycache__', '.pytest_cache'])}
    report = {
        'status': 'full placement derivation stopped; local-candidate discovery, source-placement and WKT controls executed',
        'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
        'inputs': inputs, 'source_files': source_files, 'completion': completion,
        'stopping_reason': stopping_reason,
        'proposal_quality': json.loads((root/'proposal-quality.json').read_text()),
        'tests': {'passed': len(cases), 'failed': 0}, 'scope_controls': rows, 'origin_metrics': origin_metrics,
        'scope_queries_per_reader': sum(x['queries'] for x in rows),
        'discovery_readers': ['headless OpenUSD', 'native OpenUSD', 'live OV stage'],
        'native_executable_sha256': sha(native_exe),
        'origin_coordinate_cases_per_reader': sum(row['kind'] == 'origin_coordinates' for row in rows),
        'origin_coordinate_queries_per_reader': sum(row['queries'] for row in rows if row['kind']=='origin_coordinates'),
        'source_placement_cases_per_reader': sum(row['kind'] == 'placement_values' for row in rows),
        'wkt_profile': {
            'implementation': 'Lossless lexical normalization; strict PROJ grammar reader, no PROJ writer in serialization',
            'test_cases': sum('test_wkt_contracts' in case.attrib.get('classname', '') for case in cases),
            'coverage': ['padding, case and delimiter variants', 'preferred keyword aliases',
                         'exact decimals and exponent spelling', 'quoted metadata and escaped quotes',
                         'frame epochs', 'fixed-point validation', 'semantic equivalence versus text identity',
                         'invalid/unknown syntax rejection', 'coordinate-epoch rejection'],
            'limitations': ['Context-sensitive legacy UNIT aliases explicitly unsupported; their kind is not guessed.',
                            'This is one normalizer and a bounded strict-reader profile, not proof of support for all OGC WKT productions.'],
        },
        'placement_runtime_jobs': 0, 'hydra_placement_jobs': 0, 'ov_placement_jobs': 0,
        'exports': [], 'geodetic_accuracy_claim': False, 'source_files_unchanged': True,
        'limitations': [
            'This run executes the local review candidate, not the published proposal alone; detailed draft choices are not group adoption.',
            'Direct coordinate controls resolve only adjustment-free anchor origins; provider positions are illustrative model placements, not an answer to measurement association. All three readers share PROJ, not independent geodetic engines.',
            'Source placement controls read fields, fallbacks and Core interpolation; they do not compute resolved positions or frames.',
            'Native USD discovery is not Hydra placement or rendering. Live OV discovery is not resolved geometry ingestion.',
            'Adjustment frame, stage/basis mapping, measurement-coordinate association and dependency declaration stop dependent full derivation; geographic scene-frame scope is also unresolved.',
            'Unit-quaternion inputs use Core semantics; a full validator numerical policy for near-unit authored values is not claimed and no acceptance epsilon is invented.',
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


def distance(left,right,factors):
    return math.sqrt(sum(((a-b)*f)**2 for a,b,f in zip(left,right,factors)))

def check_job(result,job):
    if job.get('kind')!='origin_coordinates':
        assert_results(result['queries'],job['expected']); return
    assert len(result['queries'])==len(job['expected'])
    for actual,expected in zip(result['queries'],job['expected']):
        if not expected['success']: assert_results(actual,expected); continue
        assert actual['prim']==expected['prim'] and actual['success']
        assert distance(actual['coordinates'],expected['coordinates'],job['output_length_factors'])<=job['acceptance_metres'],(job['name'],actual,expected)
        assert actual['operation_definition'] and actual['engine']=='PROJ'
        assert actual['operation_accuracy_metres'] is None or actual['operation_accuracy_metres']>=0

def origin_agreement(jobs,headless,native,ov):
    records=[]
    for job,h,n,o in zip(jobs,headless,native,ov):
        if job.get('kind')!='origin_coordinates': continue
        good=[index for index,row in enumerate(job['expected']) if row['success']]
        discrepancies=[]; agreements=[]; definitions=[]
        for index in good:
            rows=[consumer['queries'][index] for consumer in [h,n,o]]
            # These particular controls must realize identical pipeline tokens.
            normalized=[' '.join(row['operation_definition'].replace('+','').split()) for row in rows]
            assert len(set(normalized))==1,('Different operations; do not call this numerical drift',job['name'],normalized)
            definitions.append(rows[0]['operation_definition'])
            for row in rows:
                discrepancies.append(distance(row['coordinates'],job['expected'][index]['coordinates'],job['output_length_factors']))
            agreements.extend(distance(rows[0]['coordinates'],row['coordinates'],job['output_length_factors']) for row in rows[1:])
        records.append({'name':job['name'],'successful_origins':len(good),'expected_failures':len(job['expected'])-len(good),
                        'acceptance_metres':job['acceptance_metres'],'max_reference_discrepancy_metres':max(discrepancies,default=0.),
                        'max_reader_agreement_metres':max(agreements,default=0.),'equivalent_pipeline_tokens_checked':True,
                        'operations':sorted(set(definitions)),
                        'reference':'Analytic WGS84 equatorial ECEF' if 'interpolation' in job['name'] else 'Provider PROJ-generated CSV; intake/rounding reference, not survey truth'})
    return records
