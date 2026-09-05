"""Settings and production configuration tests."""

from app.config import Settings


def test_frontend_url_merged_into_cors_origins():
    settings = Settings(
        frontend_url="https://earningspulse.vercel.app",
        cors_origins=["http://localhost:3000"],
    )
    assert "https://earningspulse.vercel.app" in settings.cors_origins
    assert "http://localhost:3000" in settings.cors_origins


def test_frontend_url_not_duplicated_in_cors():
    settings = Settings(
        frontend_url="https://earningspulse.vercel.app",
        cors_origins=[
            "http://localhost:3000",
            "https://earningspulse.vercel.app",
        ],
    )
    assert settings.cors_origins.count("https://earningspulse.vercel.app") == 1


def test_cors_origin_regex_can_be_configured_for_preview_deployments():
    settings = Settings(cors_origin_regex=r"https://.*\.vercel\.app")

    assert settings.cors_origin_regex == r"https://.*\.vercel\.app"


def test_prism_enabled_requires_key_and_project():
    assert Settings(prism_api_key=None, prism_project_id="proj").prism_enabled is False
    assert Settings(prism_api_key="pt-sk-test", prism_project_id=None).prism_enabled is False
    assert Settings(prism_api_key="pt-sk-test", prism_project_id="proj").prism_enabled is True


def test_prism_required_can_be_toggled():
    assert Settings(prism_required=True).prism_required is True
    assert Settings(prism_required=False).prism_required is False
