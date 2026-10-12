"""Checks derived from the writer/reader contract and actual proposal examples."""
from pathlib import Path
import re, json
import numpy as np
from pxr import Usd
from pyproj import CRS
from review.wkt_profile import normalize, strict_crs, UnsupportedWKT

def variants(value):
    def outside(fn):
        return ''.join(t if i%2 else fn(t) for i,t in enumerate(re.split(r'("(?:[^"]|"")*")',value)))
    return {
        'padding':outside(lambda t:re.sub(r'([\[\],])',r' \1 \n',t)),
        'case':outside(str.lower),
        'parentheses':outside(lambda t:t.replace('[','(').replace(']',')')),
        'decimal':value.replace('LENGTHUNIT["metre",1]', 'LENGTHUNIT["metre",1.000E0]'),
        'quoted-name':value.replace('"WGS 84"','"COORDINATEMETADATA is only a quoted name"',1),
    }

def add_jobs(jobs,directory):
    base=next(j for j in jobs if j['name']=='basis-Z-1')
    original=Usd.Stage.Open(base['stage'])
    value=original.GetPrimAtPath('/World/Model').GetAttribute('crs:wkt').Get()
    for name,wkt in variants(value).items():
        path=directory/('wkt-'+name+'.usda');original.GetRootLayer().Export(str(path))
        stage=Usd.Stage.Open(str(path));stage.GetPrimAtPath('/World/Model').GetAttribute('crs:wkt').Set(wkt)
        stage.GetRootLayer().Save()
        jobs.append({**base,'name':'wkt-'+name,'stage':str(path),'wkt_expected':base['expected']})

def verify_examples(root):
    text=(root/'proposal/proposal-source.txt').read_text(encoding='utf-8')
    examples=re.findall(r'```lisp\n(.*?)\n```',text,re.S)
    result=[]
    for number,value in enumerate(examples,1):
        if value.lstrip().startswith('COORDINATEMETADATA['):
            try:normalize(value)
            except UnsupportedWKT:result.append({'example':number,'role':'coordinate-epoch roadmap','initial_reader':'unsupported as specified'});continue
            raise AssertionError('Coordinate epoch wrapper accepted in initial profile')
        strict_crs(value);normal=normalize(value);assert normalize(normal)==normal
        a=CRS.from_wkt(value);b=CRS.from_wkt(normal);assert a.equals(b)
        result.append({'example':number,'name':a.name,'valid':True,'normalization_idempotent':True,'axes':[(x.direction,x.unit_name) for x in a.axis_info]})
    ecef=next(x for x in examples if x.startswith('GEODCRS["ITRF2020"'))
    assert CRS.from_wkt(ecef).equals(CRS.from_epsg(9988))
    site=next(x for x in examples if x.startswith('COMPOUNDCRS["Westminster'))
    assert site.strip()==(root/'data/Colorado/03_Westminster_Site_Calibration_WKT2.txt').read_text().strip()
    assert all(('ID["EPSG",'+x+']') in site for x in ['8617','8618','1037'])
    assert [x.direction for x in CRS.from_wkt(site).axis_info]==['east','north','up']
    return result
