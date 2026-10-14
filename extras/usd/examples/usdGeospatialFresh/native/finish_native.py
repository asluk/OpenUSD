from pathlib import Path
p=Path(__file__).with_name('reader.cpp');s=p.read_text()
def change(old,new):
    global s
    assert s.count(old)==1,(old[:80],s.count(old));s=s.replace(old,new)
change('#include <limits>','#include <limits>\n#include <iomanip>\n#include <sstream>\n#include "interval.h"')
change('Vec r=angles*(PI/180);','Vec r(std::fmod(angles[0],720)*PI/180,std::fmod(angles[1],720)*PI/180,std::fmod(angles[2],720)*PI/180);')
change('auto qa=quat(placement(p,"crs:orientation",UsdTimeCode(lo)));','Vec va=placement(p,"crs:orientation",UsdTimeCode(lo));auto qa=quat(va);')
change('auto qb=quat(placement(p,"crs:orientation",UsdTimeCode(hi)));','Vec vb=placement(p,"crs:orientation",UsdTimeCode(hi));auto qb=quat(vb);')
start=s.index('double eps=std::numeric_limits<double>::epsilon();double uncertainty=39*eps;')
end=s.index('double f=(x-lo)/(hi-lo);',start)
s=s[:start]+'''auto enclosure=certified::dot(va,vb);if(enclosure.lo<=0&&enclosure.hi>=0){std::ostringstream detail;detail<<std::setprecision(17)<<"Ideal-angle dot interval ["<<enclosure.lo<<","<<enclosure.hi<<"]; angular uncertainty <= "<<2*std::asin(std::min(1.,std::max(std::abs(enclosure.lo),std::abs(enclosure.hi))))<<" radians";throw Failure("ambiguous-half-turn",detail.str());}if(enclosure.hi<0){qb=-qb;dot=-dot;}''' + s[end:]
change('if(source.dim!=3)throw Failure("missing-height","Model placement requires 3D");','if(!std::isfinite(unit)||unit<=0)throw Failure("invalid-stage-units","Stage units must be positive finite");if(UsdGeomGetStageUpAxis(stage)!=TfToken("Y")&&UsdGeomGetStageUpAxis(stage)!=TfToken("Z"))throw Failure("unsupported-stage-up","Stage axis must be Y or Z");if(source.dim!=3)throw Failure("missing-height","Model placement requires 3D");')
change('double accuracy=proj_coordoperation_get_accuracy(e.ctx,actual);','std::string pipeline=definition?definition:"";for(auto term:{"+proj=deformation","+dx=","+dy=","+dz=","+drx=","+dry=","+drz=","+ds="})if(pipeline.find(term)!=pipeline.npos){proj_destroy(used);throw Failure("deferred-epoch-operation","Operation requires deferred coordinate-epoch interpretation");}double accuracy=proj_coordoperation_get_accuracy(e.ctx,actual);')
change('{"source_reader",JsValue("native C++ USD stage reader")}','{"coordinate_wkt",JsValue(q.wkt)},{"source_reader",JsValue("native C++ USD stage reader")}')
# Independent spelling tables now cover the same Annex-B enum profile.
change('{"PROJECTEDCRS","PROJCRS"}}','{"PROJECTEDCRS","PROJCRS"},{"VERTICALCRS","VERTCRS"},{"ENGINEERINGCRS","ENGCRS"},{"TEMPORALCRS","TIMECRS"}}')
change('{"GEOCENTRICZ","geocentricZ"}}','{"GEOCENTRICZ","geocentricZ"},{"PARAMETRIC","parametric"},{"TEMPORAL","temporal"},{"ORDINAL","ordinal"},{"AFFINE","affine"},{"CYLINDRICAL","cylindrical"},{"POLAR","polar"},{"FUTURE","future"},{"PAST","past"},{"UNSPECIFIED","unspecified"},{"CLOCKWISE","clockwise"},{"COUNTERCLOCKWISE","counterClockwise"},{"AWAYFROM","awayFrom"},{"TOWARDS","towards"},{"COLUMNPOSITIVE","columnPositive"},{"ROWPOSITIVE","rowPositive"},{"DISPLAYRIGHT","displayRight"},{"DISPLAYLEFT","displayLeft"},{"DISPLAYUP","displayUp"},{"DISPLAYDOWN","displayDown"},{"FORWARD","forward"},{"AFT","aft"},{"PORT","port"},{"STARBOARD","starboard"}}')
p.write_text(s)
