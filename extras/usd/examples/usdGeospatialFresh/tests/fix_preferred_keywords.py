from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'src/wkt.py';s=p.read_text();start=s.index('PREFERRED = ');end=s.index('\nENUM =',start)
s=s[:start]+'''PREFERRED = {'PRIMEMERIDIAN':'PRIMEM','GEODETICDATUM':'DATUM','TRF':'DATUM','VERTICALDATUM':'VDATUM','VRF':'VDATUM','ENGINEERINGDATUM':'EDATUM','TIMEDATUM':'TDATUM','PARAMETRICDATUM':'PDATUM','GEODETICCRS':'GEODCRS','GEOGRAPHICCRS':'GEOGCRS','PROJECTEDCRS':'PROJCRS','VERTICALCRS':'VERTCRS','ENGINEERINGCRS':'ENGCRS'}''' +s[end:];p.write_text(s)
p=ROOT/'native/reader.cpp';s=p.read_text();start=s.index(' const std::map<std::string,std::string>alias');end=s.index('\n const std::map<std::string,std::string>enums',start)
s=s[:start]+''' const std::map<std::string,std::string>alias{{"PRIMEMERIDIAN","PRIMEM"},{"GEODETICDATUM","DATUM"},{"TRF","DATUM"},{"VERTICALDATUM","VDATUM"},{"VRF","VDATUM"},{"ENGINEERINGDATUM","EDATUM"},{"TIMEDATUM","TDATUM"},{"PARAMETRICDATUM","PDATUM"},{"GEODETICCRS","GEODCRS"},{"GEOGRAPHICCRS","GEOGCRS"},{"PROJECTEDCRS","PROJCRS"},{"VERTICALCRS","VERTCRS"},{"ENGINEERINGCRS","ENGCRS"}};''' +s[end:];p.write_text(s)
# Test expected spelling comes from OGC keyword productions, not the algorithm.
p=ROOT/'tests/test_contract.py';s=p.read_text();s=s.replace("'GEODETICDATUM[", "'DATUM[").replace("'PRIMEMERIDIAN[", "'PRIMEM[");p.write_text(s)
