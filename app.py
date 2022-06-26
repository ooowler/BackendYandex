import aioredis
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi_limiter import FastAPILimiter
from starlette.responses import PlainTextResponse

from core.routes import routes

# from starlette.responses import Response

app = FastAPI(docs_url='/')

app.include_router(routes)



@app.on_event("startup")
async def startup():
    # redis = await aioredis.create_redis_pool("redis://redis_api") # vps
    redis = await aioredis.create_redis_pool("redis://default:redispw@localhost:55000") #local
    await FastAPILimiter.init(redis)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str('Невалидная схема документа или входные данные не верны.'), status_code=400)

if __name__ == '__main__':
    # uvicorn.run("app:app", host="0.0.0.0", port=8000) # vps
    uvicorn.run("app:app", host="127.0.0.1", port=8000)  # local
