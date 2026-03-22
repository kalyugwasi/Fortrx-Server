from fastapi import FastAPI
from app.database import Base,engine
import app.models,app.schemas,app.crypto,app.services
from app.routers import auth,keys,messages
from app.services import ensure_bucket_exists
app = FastAPI(title='Fortress')
app.include_router(keys.router)
app.include_router(auth.router)
app.include_router(messages.router)
#Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
ensure_bucket_exists()
@app.get('/')
def health():
    return {"status":"Fortress is running"}