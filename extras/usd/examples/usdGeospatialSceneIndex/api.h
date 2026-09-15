#ifndef USDGEOSPATIAL_SI_API_H
#define USDGEOSPATIAL_SI_API_H

#include <pxr/base/arch/export.h>

#if defined(PXR_STATIC)
#   define USDGEOSPATIAL_SI_API
#else
#   if defined(USDGEOSPATIAL_SI_EXPORTS)
#       define USDGEOSPATIAL_SI_API ARCH_EXPORT
#   else
#       define USDGEOSPATIAL_SI_API ARCH_IMPORT
#   endif
#endif

#endif
