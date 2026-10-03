from pxr import UsdValidation,Sdf
from geobuild.model import validate
def check(stage,timeRange):
    try:issues=validate(stage)
    except Exception as e:issues=[('/',f'Validator could not complete: {e}')]
    return [UsdValidation.ValidationError('AuthoredModel',UsdValidation.ValidationErrorType.Error,
        [UsdValidation.ValidationErrorSite(stage,Sdf.Path(path))],message) for path,message in issues]
UsdValidation.ValidationRegistry().RegisterPluginStageValidator('geospatialValidation:AuthoredGeospatial',check)
