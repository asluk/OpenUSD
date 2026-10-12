import pytest
from pathlib import Path
from pxr import Gf
from review.sebastien_controls import variants,verify_examples
from review.wkt_profile import validate_readable,validate_normal_form,WKTNormalizationWarning,WKTProfileError
from review.fixture_definitions import EXACT
from review.test_split_feedback import simple,ECEF
from candidate.runtime import Runtime,ContractError

@pytest.mark.parametrize('variant',list(variants(EXACT)))
def test_reader_accepts_supported_non_normal_text(tmp_path,variant):
    stage=simple(tmp_path,'reader-'+variant)
    wkt=variants(ECEF)[variant]
    stage.GetPrimAtPath('/World/Model').GetAttribute('crs:wkt').Set(wkt)
    before=stage.GetRootLayer().ExportToString()
    if variant=='quoted-name':
        value=Runtime(stage,ECEF,0).placement(stage.GetPrimAtPath('/World/Model'),Gf.Vec3d(0))
    else:
        with pytest.warns(WKTNormalizationWarning):
            value=Runtime(stage,ECEF,0).placement(stage.GetPrimAtPath('/World/Model'),Gf.Vec3d(0))
    assert list(value[0])==pytest.approx([6378137,0,0],abs=1e-8)
    assert stage.GetRootLayer().ExportToString()==before

def test_actual_proposal_examples_have_stated_meaning():
    assert len(verify_examples(Path(__file__).resolve().parents[1]))>=6

def test_writer_error_is_reader_warning():
    padded=' '+EXACT+' '
    with pytest.raises(WKTProfileError):validate_normal_form(padded)
    with pytest.warns(WKTNormalizationWarning):assert validate_readable(padded)==padded

def test_invalid_wkt_is_not_downgraded_to_spelling_warning():
    with pytest.raises(WKTProfileError):validate_readable(EXACT[:-1])
