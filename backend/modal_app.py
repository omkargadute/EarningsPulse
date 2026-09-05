"""Modal deployment entry point for the EarningsPulse FastAPI API."""

from pathlib import Path

import modal

BACKEND_DIR = Path(__file__).resolve().parent

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_sync(
        str(BACKEND_DIR),
        frozen=True,
        extra_options="--no-dev",
    )
    .workdir("/root")
    .add_local_dir(BACKEND_DIR / "app", "/root/app")
    .add_local_dir(BACKEND_DIR / "demo", "/root/demo")
)

app = modal.App("earningspulse-api")

secrets: list[modal.Secret] = []
env_file = BACKEND_DIR / ".env"
root_env_file = BACKEND_DIR.parent / ".env"
if env_file.exists():
    secrets.append(modal.Secret.from_dotenv(path=env_file))
elif root_env_file.exists():
    secrets.append(modal.Secret.from_dotenv(path=root_env_file))


@app.function(
    image=image,
    secrets=secrets,
    env={
        "ENVIRONMENT": "production",
        # Initial testing may use any Vercel preview or production hostname.
        # Replace this with an exact FRONTEND_URL once the new domain is known.
        "CORS_ORIGIN_REGEX": r"https://.*\.vercel\.app",
        "TRACE_LOG_DIR": "/tmp/logs/traces",
    },
    max_containers=1,
    scaledown_window=300,
    timeout=900,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    """Expose the existing FastAPI application as one Modal web function."""
    from app.main import app as web_app

    return web_app
