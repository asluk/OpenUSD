from pathlib import Path
import json,hashlib,re,zipfile,xml.etree.ElementTree as ET,html
W=Path('C:/Users/aluk/Documents/Codex/2026-09-21/have')
P=Path('C:/git/worktrees/geospatial-openusd-delivery/extras/usd/examples/usdGeospatialBuild')
B=W/'work/geospatial-sebastien-assessment-20261012'
O=W/'outputs/geospatial-sebastien-build-20261012'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
story=json.loads((P/'delivery/story.json').read_text(encoding='utf-8'))
readme=(P/'README.md').read_text(encoding='utf-8')
assert sha(P/'README.md')==story['readme_sha256']
for c in story['cases']:
    for key in ['question','rule','expected','observed','implication','boundary']:
        assert c[key] in readme,(c['id'],key)
    assert c['clause_heading']==(P/'proposal/proposal-source.txt').read_text(encoding='utf-8').splitlines()[c['clause_line']-1]
    if c.get('image'):assert (P/'delivery'/c['image']['path']).is_file()
main=re.sub(r'<details>.*?</details>','',readme,flags=re.S)
assert not re.search(r'what .*changed|changes since|fresh|prior .*defect|previous run|red.team',main,re.I)
assert readme.index('Source inputs and computed placement')<readme.index('Evidence and its limits')
assert all(x in readme for x in ['Inputs-only','Expected behavior','Observed result','What this says about the proposal','WKT string normalization','shared','two prototype','unverified'])
receipt_path=W/'work/geospatial-sebastien-run-20261012-v3/delivery/run-report.json'
r=json.loads(receipt_path.read_text())
assert sha(receipt_path)==story['receipt_sha256']
assert all(sha(P/f)==h for f,h in r['source_files'].items())
(O/'README.md').write_text(readme,encoding='utf-8',newline='\n')
# Local rendered reading preview. The base preserves real image paths and links.
import markdown
body=markdown.markdown(readme,extensions=['tables','fenced_code'])
page='<!doctype html><html><head><meta charset="utf-8"><base href="'+P.as_uri()+'/"><style>body{max-width:1040px;margin:48px auto;padding:0 32px;font:19px/1.6 Arial;color:#213744}h1{font-size:38px}h2{font-size:28px;margin-top:52px;color:#157c87}h3{font-size:23px;margin-top:36px}img{display:block;max-width:100%;max-height:540px;margin:26px auto;object-fit:contain}table{width:100%;border-collapse:collapse;margin:28px 0;font-size:17px}th,td{border:1px solid #d7e1e6;padding:10px;text-align:left;vertical-align:top}th{background:#213744;color:white}a{color:#157c87}code{font-size:15px;overflow-wrap:anywhere}details{border-top:1px solid #d7e1e6;padding-top:18px}</style></head><body>'+body+'</body></html>'
(B/'README-preview.html').write_text(page,encoding='utf-8')
record={'readme_sha256':story['readme_sha256'],'narrative_version':2,'cases':len(story['cases']),'frozen_files_verified':len(r['source_files']),'receipt_sha256':story['receipt_sha256'],'checks':['Complete proposal introduction precedes evidence totals','Each case contains rule, expectation, observation, implication and limit','Each case resolves to the current proposal clause','Run history isolated in supporting records','Illustrations and recorded evidence labeled','Executed inputs and immutable receipt preserved'],'visual_review':'pending'}
(B/'narrative-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
