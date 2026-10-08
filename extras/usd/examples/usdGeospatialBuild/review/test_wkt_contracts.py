"""Independent lexical expectations, not PROJ writer output as a golden file."""
import re
import pytest
from pyproj import CRS
from review.wkt_profile import normalize, validate_normal_form, WKTProfileError, UnsupportedWKT, decimal_spelling

from review.fixture_definitions import EXACT, GEOGRAPHIC


def outside_quotes(value, function):
    parts = re.split(r'("(?:[^"]|"")*")', value)
    return ''.join(v if index % 2 else function(v) for index, v in enumerate(parts))


@pytest.mark.parametrize('case', ['canonical', 'padding', 'case', 'delimiters', 'aliases', 'exponent'])
def test_spelling_variants_have_hand_specified_normal_text(case):
    variant = {
        'canonical': EXACT,
        'padding': outside_quotes(EXACT, lambda v: re.sub(r'([\[\],])', r' \1 \n', v)),
        'case': outside_quotes(EXACT, str.lower),
        'delimiters': outside_quotes(EXACT, lambda v: v.replace('[', '(').replace(']', ')')),
        'aliases': EXACT.replace('GEODCRS[', 'GEODETICCRS[').replace('PRIMEM[', 'PRIMEMERIDIAN['),
        'exponent': EXACT.replace('6378137.12345678912345', '6.37813712345678912345E6').replace('1.0]', '1E0]'),
    }[case]
    assert normalize(variant) == EXACT
    assert normalize(normalize(variant)) == EXACT


@pytest.mark.parametrize('value', [EXACT, GEOGRAPHIC])
def test_fixed_point_and_exact_numeric_precision(value):
    assert validate_normal_form(value) == value
    assert '6378137.12345678912345' in EXACT


@pytest.mark.parametrize('raw,expected', [
    ('1', '1.0'), ('1.00', '1.0'), ('1E0', '1.0'), ('-0E9', '0.0'),
    ('+001.2300E-2', '0.0123'), ('6378137.12345678912345', '6378137.12345678912345'),
])
def test_exact_decimal_convention(raw, expected):
    assert decimal_spelling(raw) == expected


def test_name_and_remark_preserved_without_false_crs_inequality():
    changed = EXACT.replace('Exact frame', 'Same coordinates, different name')
    assert normalize(changed) == changed and changed != EXACT
    assert CRS.from_wkt(changed).equals(CRS.from_wkt(EXACT))
    assert 'Keep  spaces, case, [brackets], ""quoted""' in normalize(changed)


def test_normalizer_does_not_use_lossy_engine_serialization():
    engine_text = CRS.from_wkt(EXACT).to_wkt(version='WKT2_2019', pretty=False)
    assert '6378137.12345678912345' not in engine_text
    assert normalize(EXACT) == EXACT


def test_frame_epoch_is_preserved_as_crs_metadata():
    dynamic = EXACT.replace('DATUM[', 'DYNAMIC[FRAMEEPOCH[2015.0]],DATUM[', 1)
    assert 'FRAMEEPOCH[2015.0]' in normalize(dynamic)
    assert normalize(dynamic.replace('2015.0', '2016.0')) != normalize(dynamic)


@pytest.mark.parametrize('value', [
    EXACT[:-1] + ',FUTURENODE["do not discard"]]',
    EXACT.replace('GEODCRS[', 'GEOD CRS['),
    EXACT.replace('GEODCRS[', 'GEODCRS('),
    EXACT + ' extra',
])
def test_invalid_or_unknown_syntax_never_silently_drops_information(value):
    with pytest.raises(WKTProfileError):
        normalize(value)


def test_valid_external_padding_is_not_conforming_authored_token():
    with pytest.raises(WKTProfileError, match='fixed point'):
        validate_normal_form(' ' + EXACT + ' ')


def test_coordinate_epoch_wrapper_is_explicitly_unsupported():
    with pytest.raises(UnsupportedWKT, match='CRS-only'):
        normalize('COORDINATEMETADATA[' + GEOGRAPHIC + ',EPOCH[2026.0]]')


def test_context_sensitive_unit_alias_is_not_guessed():
    with pytest.raises(UnsupportedWKT, match='UNIT alias'):
        normalize(EXACT.replace('LENGTHUNIT[', 'UNIT['))
