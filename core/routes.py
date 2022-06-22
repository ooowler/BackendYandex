from fastapi import APIRouter, Depends


from routess import academ

routes = APIRouter()

#функции для работы с юзером
routes.include_router(academ.router)
