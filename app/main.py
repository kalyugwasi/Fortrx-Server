import asyncio
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from app.database import Base,engine,SessionLocal
import app.models,app.schemas,app.crypto,app.services
from app.routers import auth,keys,messages,ws,safety
from app.services import ensure_bucket_exists,purge_expired_messages
from app.middleware import limiter,SecurityHeadersMiddleware

app = FastAPI(title='Fortrx')

app.include_router(keys.router)
app.include_router(auth.router)
app.include_router(messages.router)
app.include_router(ws.router)
app.include_router(safety.router)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)

#Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

ensure_bucket_exists()
async def expired_message_cleanup():
    print("Cleanup loop")
    while True:
        await asyncio.sleep(60)
        db = SessionLocal()
        try:
            purge_expired_messages(db)
        except Exception as e:
            print(f"Cleanup error: {e}")
        finally:
            db.close()
@app.get('/')
async def health():
    ensure_bucket_exists()
    asyncio.create_task(expired_message_cleanup())
    return {"status":"Fortrx is running"}


# docker run -d --name localstack -p 4566:4566 localstack/localstac
# docker run -d --name minio -p 4566:4566 quay.io/minio/minio server /data --address ":4566"
# docker run -p 6379:6379 redis:alpine