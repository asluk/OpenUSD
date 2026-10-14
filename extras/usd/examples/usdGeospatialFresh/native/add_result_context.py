from pathlib import Path
p=Path(__file__).with_name('reader.cpp');s=p.read_text()
def change(a,b):
 global s
 assert s.count(a)==1,(a[:65],s.count(a));s=s.replace(a,b)
change('std::vector<double>units;int dim=0;','std::vector<double>units;std::vector<std::string>unitNames;int dim=0;')
change('std::vector<double>rawUnits;','std::vector<double>rawUnits;std::vector<std::string>rawNames;')
change('const char*direction=nullptr;double unit=0;proj_cs_get_axis_info(e.ctx,cs,i,nullptr,nullptr,&direction,&unit,nullptr,nullptr,nullptr);','const char*direction=nullptr;const char*unitName=nullptr;double unit=0;proj_cs_get_axis_info(e.ctx,cs,i,nullptr,nullptr,&direction,&unit,&unitName,nullptr,nullptr);rawNames.push_back(unitName?unitName:"unknown");')
change('for(int i:order)units.push_back(rawUnits[i]);','for(int i:order){units.push_back(rawUnits[i]);unitNames.push_back(rawNames[i]);}')
marker='Vec convert(Engine&e,'
at=s.index(marker)
s=s[:at]+'''Obj result(CRS&q,Arr coordinates,Arr operations){Arr units;for(auto&name:q.unitNames)units.push_back(JsValue(name));return Obj{{"success",JsValue(true)},{"coordinates",JsValue(coordinates)},{"operations",JsValue(operations)},{"coordinate_wkt",JsValue(q.wkt)},{"units",JsValue(units)},{"source_reader",JsValue("native C++ USD stage reader")},{"approximation",JsValue("Pointwise evaluation; no continuous-domain certificate")}};}
''' +s[at:]
change('return JsValue(Obj{{"success",JsValue(true)},{"coordinates",JsValue(values)},{"operations",JsValue(e.operations)},{"coordinate_wkt",JsValue(q.wkt)},{"source_reader",JsValue("native C++ USD stage reader")}});','return JsValue(result(q,values,e.operations));')
change('return JsValue(Obj{{"success",JsValue(true)},{"coordinates",JsValue(values)},{"operations",JsValue(e.operations)}});','return JsValue(result(q,values,e.operations));')
change('return JsValue(Obj{{"success",JsValue(true)},{"coordinates",JsValue(out)},{"operations",JsValue(e.operations)}});','return JsValue(result(q,out,e.operations));')
# Store result context consistently in the shared-format-decoder entrypoint.
a='return JsValue(Obj{{"success",JsValue(true)},{"coordinates",JsValue(values)},{"operations",JsValue(e.operations)},{"native_selection"'
b='auto receipt=result(q,values,e.operations);receipt["native_selection"]=JsValue(Obj{{"asset",JsValue(asset.GetResolvedPath())},{"format",JsValue(format.GetString())},{"field",JsValue(field)},{"domain",JsValue(domain)}});receipt["shared_decoder"]=JsValue("Fresh native-format association decoder; no shared placement evaluator");return JsValue(receipt);}\n'
start=s.index(a);end=s.index('\nJsValue execute',start)
s=s[:start]+b+s[end:]
p.write_text(s)
