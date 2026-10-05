"""Lossless lexical normalization derived from the candidate's WKT profile.

PROJ is used as a strict syntax reader, never as the serializer. Its binary
representation cannot replace exact source decimals or quoted source metadata.
Unsupported lexical contexts fail explicitly rather than selecting a meaning.
"""
from pathlib import Path
import ctypes as C
from decimal import Decimal
import re
import pyproj


class WKTProfileError(ValueError):
    pass


class UnsupportedWKT(WKTProfileError):
    pass


# OGC 18-010r11 6.6, keyword productions and Annex B.2.2.
ALIASES = {
    'GEODETICCRS': 'GEODCRS', 'GEOGRAPHICCRS': 'GEOGCRS',
    'PROJECTEDCRS': 'PROJCRS', 'VERTICALCRS': 'VERTCRS',
    'ENGINEERINGCRS': 'ENGCRS', 'GEODETICDATUM': 'DATUM', 'TRF': 'DATUM',
    'VERTICALDATUM': 'VDATUM', 'VRF': 'VDATUM', 'ENGINEERINGDATUM': 'EDATUM',
    'SPHEROID': 'ELLIPSOID', 'PRIMEMERIDIAN': 'PRIMEM',
    'TIMEDATUM': 'TDATUM', 'TEMPORALQUANTITY': 'TIMEUNIT',
    'PARAMETRICDATUM': 'PDATUM',
}
ENUMS = {value.lower(): value for value in [
    'Cartesian', 'ellipsoidal', 'affine', 'spherical', 'vertical', 'polar',
    'cylindrical', 'linear', 'ordinal', 'parametric', 'temporalDateTime',
    'temporalCount', 'temporalMeasure', 'north', 'northNorthEast', 'northEast',
    'eastNorthEast', 'east', 'eastSouthEast', 'southEast', 'southSouthEast',
    'south', 'southSouthWest', 'southWest', 'westSouthWest', 'west',
    'westNorthWest', 'northWest', 'northNorthWest', 'up', 'down',
    'geocentricX', 'geocentricY', 'geocentricZ', 'columnPositive',
    'columnNegative', 'rowPositive', 'rowNegative', 'displayRight',
    'displayLeft', 'displayUp', 'displayDown', 'forward', 'aft', 'port',
    'starboard', 'clockwise', 'counterClockwise', 'towards', 'awayFrom',
    'future', 'past', 'unspecified', 'exact', 'wraparound',
]}
TOKEN = re.compile(r'\s+|"(?:[^"]|"")*"|[A-Za-z_][A-Za-z_0-9]*|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?|[\[\](),]')
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?\Z')


def strict_crs(value):
    """Return diagnostics without exporting or replacing the source definition."""
    root = Path(pyproj.__file__).parents[1]
    library = next((root/'pyproj.libs').glob('*proj*.dll'))
    proj = C.CDLL(str(library))
    p, s = C.c_void_p, C.c_char_p
    ss = C.POINTER(s)
    signatures = {
        'proj_context_create': (p, []), 'proj_context_destroy': (p, [p]),
        'proj_context_set_database_path': (C.c_int, [p, s, ss, ss]),
        'proj_create_from_wkt': (p, [p, s, ss, C.POINTER(ss), C.POINTER(ss)]),
        'proj_destroy': (p, [p]), 'proj_string_list_destroy': (None, [ss]),
        'proj_is_crs': (C.c_int, [p]),
    }
    for name, (result, args) in signatures.items():
        getattr(proj, name).restype = result
        getattr(proj, name).argtypes = args
    context = proj.proj_context_create()
    obj = None
    try:
        if not proj.proj_context_set_database_path(context,
                str(Path(pyproj.datadir.get_data_dir())/'proj.db').encode(), None, None):
            raise UnsupportedWKT('Strict syntax reader database unavailable')
        options = (s*3)(b'STRICT=YES', b'UNSET_IDENTIFIERS_IF_INCOMPATIBLE_DEF=NO', None)
        warnings, errors = ss(), ss()
        obj = proj.proj_create_from_wkt(context, value.encode('utf-8'), options,
                                       C.byref(warnings), C.byref(errors))
        diagnostics = []
        for array in [warnings, errors]:
            values = []
            if array:
                index = 0
                while array[index]:
                    values.append(array[index].decode('utf-8'))
                    index += 1
                proj.proj_string_list_destroy(array)
            diagnostics.append(values)
        if not obj or diagnostics[1]:
            raise WKTProfileError('Strict WKT grammar check failed: ' + '; '.join(diagnostics[0] + diagnostics[1]))
        if diagnostics[0]:
            raise UnsupportedWKT('Strict reader cannot certify this form: ' + '; '.join(diagnostics[0]))
        if not proj.proj_is_crs(obj):
            raise UnsupportedWKT('Initial profile requires CRS-only WKT; coordinate epochs are deferred')
        return {'reader': 'PROJ ' + pyproj.proj_version_str,
                'strict': True, 'warnings': [], 'grammar_errors': []}
    finally:
        if obj:
            proj.proj_destroy(obj)
        proj.proj_context_destroy(context)


def decimal_spelling(raw, integer=False):
    value = Decimal(raw)
    if integer:
        if value != value.to_integral_value():
            raise WKTProfileError('Integer production has a noninteger value')
        return str(int(value))
    if value.is_zero():
        return '0.0'
    text = format(value, 'f')
    if text.startswith('+'):
        text = text[1:]
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text if '.' in text else text + '.0'


def normalize(value):
    if re.match(r'^\s*COORDINATEMETADATA\s*[\[(]', value, re.I):
        raise UnsupportedWKT('CRS-only profile; coordinate epochs are deferred')
    strict_crs(value)
    tokens = []
    cursor = 0
    while cursor < len(value):
        match = TOKEN.match(value, cursor)
        if not match:
            raise UnsupportedWKT('Unsupported lexical production at character ' + str(cursor))
        token = match[0]
        cursor = match.end()
        if not token.isspace():
            tokens.append(token)
    index = 0

    def node():
        nonlocal index
        if index >= len(tokens) or not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', tokens[index]):
            raise WKTProfileError('Expected WKT keyword')
        keyword = ALIASES.get(tokens[index].upper(), tokens[index].upper())
        if keyword == 'UNIT':
            raise UnsupportedWKT('Context-sensitive UNIT alias requires a typed grammar reader; no unit kind guessed')
        index += 1
        if index >= len(tokens) or tokens[index] not in ['[', '(']:
            raise WKTProfileError('Expected WKT delimiter')
        closing = ']' if tokens[index] == '[' else ')'
        index += 1
        items = []
        while index < len(tokens) and tokens[index] != closing:
            token = tokens[index]
            if token.startswith('"'):
                items.append(token)
                index += 1
            elif NUMBER.fullmatch(token):
                integer = (keyword == 'CS' and len(items) == 1) or keyword == 'ORDER' or (keyword == 'ID' and len(items) == 1)
                items.append(decimal_spelling(token, integer=integer))
                index += 1
            elif index + 1 < len(tokens) and tokens[index + 1] in ['[', '(']:
                items.append(node())
            elif token.lower() in ENUMS:
                items.append(ENUMS[token.lower()])
                index += 1
            else:
                raise UnsupportedWKT('Unsupported enumeration or production: ' + token)
            if index < len(tokens) and tokens[index] == ',':
                index += 1
            elif index >= len(tokens) or tokens[index] != closing:
                raise WKTProfileError('Expected separator or matching delimiter')
        if index >= len(tokens):
            raise WKTProfileError('Unclosed WKT node')
        index += 1
        return keyword + '[' + ','.join(items) + ']'

    result = node()
    if index != len(tokens):
        raise WKTProfileError('Trailing WKT input')
    strict_crs(result)
    return result


def validate_normal_form(value):
    normalized = normalize(value)
    if normalized != value:
        raise WKTProfileError('Authored WKT is not a fixed point of the candidate normal form')
    return normalized
