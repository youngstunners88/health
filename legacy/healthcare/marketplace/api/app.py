import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from engine.registry import (
    SkillRegistry,
    SkillNotFoundError,
    SkillAlreadyInstalledError,
    DependencyResolutionError,
    SkillValidationError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("marketplace-api")

app = FastAPI(title="Healthcare Marketplace API", version="1.0.0")
registry = SkillRegistry()

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _read_template(name):
    path = os.path.join(TEMPLATE_DIR, name)
    with open(path, "r") as f:
        return f.read()


class SkillPublishRequest(BaseModel):
    name: str
    description: str
    version: str
    author: str
    category: str
    tags: list[str]
    install_command: str
    dependencies: list[str] = []


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=_read_template("marketplace_dashboard.html"))


@app.get("/api/skills")
async def list_skills(category: str = ""):
    try:
        if category:
            skills = registry.search_skills(query="", category=category)
        else:
            skills = registry.search_skills("")
        stats = registry.get_statistics()
        return {"skills": skills, "stats": stats, "total": len(skills)}
    except Exception as e:
        logger.exception("Failed to list skills")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/{skill_id}")
async def get_skill(skill_id: str):
    try:
        return registry.get_skill_details(skill_id)
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to get skill %s", skill_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills", status_code=201)
async def publish_skill(skill: SkillPublishRequest):
    try:
        result = registry.publish_skill(skill.model_dump())
        return {"skill_id": result["id"], "status": "published", "skill": result}
    except SkillValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to publish skill")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/{skill_id}/install")
async def install_skill(skill_id: str):
    try:
        result = registry.install_skill(skill_id)
        return {"skill_id": skill_id, "status": "installed", "details": result}
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SkillAlreadyInstalledError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DependencyResolutionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to install skill %s", skill_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/skills/{skill_id}/install")
async def uninstall_skill(skill_id: str):
    try:
        result = registry.uninstall_skill(skill_id)
        return {"skill_id": skill_id, "status": "uninstalled", "details": result}
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to uninstall skill %s", skill_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search_skills(q: str = "", category: str = ""):
    try:
        results = registry.search_skills(q, category)
        return {
            "query": q,
            "category": category,
            "count": len(results),
            "skills": results,
        }
    except Exception as e:
        logger.exception("Failed to search skills")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def stats():
    try:
        return registry.get_statistics()
    except Exception as e:
        logger.exception("Failed to get stats")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/installed")
async def get_installed():
    try:
        skills = registry.get_installed_skills()
        return {"installed": skills, "total": len(skills)}
    except Exception as e:
        logger.exception("Failed to get installed skills")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="info")
