from fastapi import APIRouter
from app.api.v1.routes.farm_routes import router as farm_router
from app.api.v1.routes.farm_visit_routes import router as farm_visit_router
from app.api.v1.routes.admin_router import router as admin_router
from app.api.v1.routes.scheme_application_routes import router as application_router
from app.api.v1.routes.farmer_scheme_router import router as farmer_scheme_router
from app.api.v1.routes.model_routes import router as model_router
from app.api.v1.routes.blockchain import router as payout_router

router = APIRouter()
router.include_router(farm_router, prefix="/farm", tags=["Farm"])
router.include_router(farm_visit_router, prefix="/farm/visit", tags=["Farm Visit"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
router.include_router(application_router, prefix="/scheme", tags=["Scheme Applications"])
router.include_router(farmer_scheme_router)
router.include_router(model_router, prefix="/model", tags=["Model"])
router.include_router(farm_router, prefix="/api/v1/farm", tags=["farm"])
router.include_router(model_router, prefix="/api/v1/model", tags=["model"])
router.include_router(payout_router, prefix="/api/v1")
