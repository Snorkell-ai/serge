import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from serge.database import SessionLocal, engine, seed_db
from serge.models.settings import Settings
from serge.routers.auth import auth_router
from serge.routers.chat import chat_router
from serge.routers.model import model_router
from serge.routers.ping import ping_router
from serge.routers.user import user_router
from starlette.responses import FileResponse

from serge.models import user as user_models

# Configure logging settings

# Define a logger for the current mo
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")

settings = Settings()

tags_metadata = [
    {
        "name": "misc.",
        "description": "Miscellaneous endpoints that don't fit anywhere else",
    },
    {
        "name": "chats",
        "description": "Used to manage chats",
    },
]

description = """
Serge answers your questions poorly using LLaMA/alpaca. 🚀
"""

origins = [
    "http://localhost",
    "http://api:9124",
    "http://localhost:9123",
    "http://localhost:9124",
]

# Seed the database
user_models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Serge", version="0.0.1", description=description, tags_metadata=tags_metadata)

api_app = FastAPI(title="Serge API")
api_app.include_router(chat_router)
api_app.include_router(ping_router)
api_app.include_router(model_router)
api_app.include_router(auth_router)
api_app.include_router(user_router)
app.mount("/api", api_app)

# handle serving the frontend as static files in production
if settings.NODE_ENV == "production":

    @app.middleware("http")
    async def add_custom_header(request, call_next):
        """Add a custom header for specific HTTP responses.

        This function processes an incoming HTTP request and checks the response
        status code. If the status code is 404 (Not Found), it returns a custom
        HTML file located at "static/200.html" instead of the default 404
        response. For all other status codes, it returns the original response.

        Args:
            request: The incoming HTTP request object.
            call_next: A callable that takes the request and returns the response.

        Returns:
            Response: The modified response object, either the original or the custom 200 HTML
                file.
        """

        response = await call_next(request)
        if response.status_code == 404:
            return FileResponse("static/200.html")
        return response

    @app.exception_handler(404)
    def not_found(request, exc):
        return FileResponse("static/200.html")

    async def homepage(request):
        return FileResponse("static/200.html")

    app.route("/", homepage)
    app.mount("/", StaticFiles(directory="static"))

    start_app = app
else:
    start_app = api_app


@start_app.on_event("startup")
async def start_database():
    """Start the database by cleaning up temporary weight files and seeding the
    database.

    This function first identifies and removes all temporary files with a
    '.tmp' extension from the specified weights directory. After cleaning up
    the temporary files, it establishes a database session and seeds the
    database with initial data.
    """

    WEIGHTS = "/usr/src/app/weights/"
    files = os.listdir(WEIGHTS)
    files = list(filter(lambda x: x.endswith(".tmp"), files))

    for file in files:
        os.remove(WEIGHTS + file)

    db = SessionLocal()
    seed_db(db)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
