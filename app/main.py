from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.broker import broker, declare_configuration


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.start()
    await declare_configuration(broker)
    # startup
    yield
    # shutdown


app = FastAPI(title='Payment Processing Service', lifespan=lifespan)
app.include_router(router)


@app.get('/health', include_in_schema=False)
async def health() -> dict[str, str]:
    return {'status': 'ok'}


# для локального запуска
if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)
