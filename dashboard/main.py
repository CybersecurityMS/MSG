from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dashboard.data_access import compute_stats, load_alerts

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="SOC AI Dashboard")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/")
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/alerts")
def api_alerts() -> JSONResponse:
    alerts = load_alerts()
    return JSONResponse([a.model_dump(mode="json") for a in alerts])


@app.get("/api/stats")
def api_stats() -> JSONResponse:
    alerts = load_alerts()
    return JSONResponse(compute_stats(alerts))
