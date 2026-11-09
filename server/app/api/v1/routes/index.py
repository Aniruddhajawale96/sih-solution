from fastapi import APIRouter
from app.api.v1.routes.farm_routes import router as farm_router
from app.api.v1.routes.farm_visit_routes import router as farm_visit_router
from app.api.v1.routes.admin_router import router as admin_router
from app.api.v1.routes.scheme_application_routes import router as application_router
from app.api.v1.routes.farmer_scheme_router import router as farmer_scheme_router
from app.api.v1.routes.model_routes import router as model_router
from app.api.v1.routes.blockchain import router as payout_router

router = APIRouter()

# Final paths under /api/v1:
# /api/v1/farm/...
router.include_router(farm_router, prefix="/farm", tags=["Farm"])
# /api/v1/farm/visit/...
router.include_router(farm_visit_router, prefix="/farm/visit", tags=["Farm Visit"])
# /api/v1/admin/...
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
# /api/v1/scheme/applications/...
router.include_router(application_router, prefix="/scheme", tags=["Scheme Applications"])
# /api/v1/farmer-schemes/...  (prefix already set on the router itself)
router.include_router(farmer_scheme_router)
# /api/v1/model/...
router.include_router(model_router, prefix="/model", tags=["Model"])
# /api/v1/payout/...  (prefix "/payout" already set on the router itself)
router.include_router(payout_router)
