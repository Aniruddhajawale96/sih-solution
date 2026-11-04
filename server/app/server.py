from fastapi import FastAPI
from app.api.v1.routes.index import router as v1_router
from app.config.settings import settings
from app.core.database import close_mongo_connection, connect_to_mongo

app = FastAPI(title=settings.APP_NAME)

app.include_router(
    v1_router,
    prefix=settings.API_V1_PREFIX
)



@app.on_event("startup")
async def startup():
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()

@app.get("/")
def health():
    return {"status": "ok"}
