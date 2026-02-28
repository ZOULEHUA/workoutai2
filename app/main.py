import json
import os
import random
import re
import sqlite3
import string
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.planner import (
    build_non_strength_plan,
    build_strength_cycle_plan,
    daily_macro,
    extract_posture_insights,
)
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "generated"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "workoutai.db"

for path in [DATA_DIR, UPLOAD_DIR]:
    path.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="WorkoutAI Planner")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS beta_codes (
                code TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                used_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                plan_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


init_db()


class GenerateCodeRequest(BaseModel):
    admin_secret: str
    count: int = 1


class GenerateCodeResponse(BaseModel):
    codes: list[str]


def require_admin_secret(secret: str) -> None:
    expected = os.getenv("ADMIN_SECRET", "change-me-admin-secret")
    if secret != expected:
        raise HTTPException(status_code=403, detail="Invalid admin secret")


def create_numeric_code(length: int = 8) -> str:
    return "".join(random.choice(string.digits) for _ in range(length))


@app.post("/api/beta/generate", response_model=GenerateCodeResponse)
def generate_beta_codes(req: GenerateCodeRequest) -> GenerateCodeResponse:
    require_admin_secret(req.admin_secret)
    count = min(max(req.count, 1), 100)
    codes: list[str] = []

    with sqlite3.connect(DB_PATH) as conn:
        for _ in range(count):
            code = create_numeric_code()
            while conn.execute("SELECT 1 FROM beta_codes WHERE code = ?", (code,)).fetchone():
                code = create_numeric_code()
            conn.execute(
                "INSERT INTO beta_codes (code, created_at) VALUES (?, ?)",
                (code, datetime.utcnow().isoformat()),
            )
            codes.append(code)
    return GenerateCodeResponse(codes=codes)


def validate_beta_code(code: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT code, active, used_count FROM beta_codes WHERE code = ?", (code,)
        ).fetchone()
        if not row or row[1] != 1:
            raise HTTPException(status_code=403, detail="Beta code invalid or inactive")
        conn.execute(
            "UPDATE beta_codes SET used_count = used_count + 1 WHERE code = ?",
            (code,),
        )


def parse_customer_text(text: str) -> dict[str, str]:
    patterns = {
        "name": r"姓名[:：\s]*([^\n,，]+)",
        "gender": r"性别[:：\s]*([^\n,，]+)",
        "height_cm": r"身高[:：\s]*(\d+(?:\.\d+)?)",
        "weight_kg": r"体重[:：\s]*(\d+(?:\.\d+)?)",
        "goal": r"目标[:：\s]*([^\n]+)",
    }
    out = {}
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            out[key] = m.group(1).strip()
    return out


def generate_pdf(plan: dict[str, Any], pdf_path: Path) -> None:
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []

    elems.append(Paragraph("WorkoutAI 专属健身与饮食计划", styles["Title"]))
    elems.append(Spacer(1, 12))
    p = plan["profile"]
    elems.append(
        Paragraph(
            f"姓名: {p['name']} | 性别: {p['gender']} | 身高: {p['height_cm']} cm | 体重: {p['weight_kg']} kg",
            styles["Normal"],
        )
    )
    elems.append(Paragraph(f"目标: {p['goal']}", styles["Normal"]))
    elems.append(Spacer(1, 12))

    posture = plan["posture_analysis"]
    elems.append(Paragraph(f"体态与身体状态: BMI {posture['bmi']}，{posture['body_status']}", styles["Normal"]))
    elems.append(Paragraph(f"薄弱肌群: {', '.join(posture['muscle_weak_points'])}", styles["Normal"]))
    elems.append(Spacer(1, 10))

    table_data = [["阶段", "碳水(g)", "蛋白(g)", "脂肪(g)", "热量(kcal)", "生肉(g)", "米饭(g)", "蔬菜(g)", "鱼油(caps)"]]
    for row in plan["diet_plan"]:
        table_data.append(
            [
                row["phase"],
                row["macro"]["carbs_g"],
                row["macro"]["protein_g"],
                row["macro"]["fat_g"],
                row["macro"]["kcal"],
                row["foods"]["生肉_g"],
                row["foods"]["米饭(熟)_g"],
                row["foods"]["绿叶蔬菜_g"],
                row["foods"]["鱼油_caps"],
            ]
        )

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f75b5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    elems.append(table)
    doc.build(elems)


@app.post("/api/parse")
def parse_text(content: str = Form(...)) -> dict[str, str]:
    return parse_customer_text(content)


@app.post("/api/plan")
async def create_plan(
    beta_code: str = Form(...),
    name: str = Form(...),
    gender: str = Form(...),
    height_cm: float = Form(...),
    weight_kg: float = Form(...),
    goal: str = Form(...),
    strength_training: bool = Form(True),
    notes: str = Form(""),
    front_image: UploadFile = File(...),
    back_image: UploadFile = File(...),
) -> dict[str, Any]:
    validate_beta_code(beta_code)

    plan_id = str(uuid.uuid4())
    front_path = UPLOAD_DIR / f"{plan_id}_front_{front_image.filename}"
    back_path = UPLOAD_DIR / f"{plan_id}_back_{back_image.filename}"
    front_path.write_bytes(await front_image.read())
    back_path.write_bytes(await back_image.read())

    posture = extract_posture_insights(weight_kg, height_cm)
    diet_plan = build_strength_cycle_plan(weight_kg) if strength_training else build_non_strength_plan(weight_kg)

    plan = {
        "plan_id": plan_id,
        "profile": {
            "name": name,
            "gender": gender,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "goal": goal,
            "strength_training": strength_training,
            "notes": notes,
        },
        "posture_analysis": posture,
        "diet_plan": diet_plan,
        "source_images": {"front": str(front_path.name), "back": str(back_path.name)},
        "case_reference": {
            "60kg_female": daily_macro(60, 3.0, 1.5),
            "80kg_male": daily_macro(80, 2.5, 2.0),
        },
    }

    pdf_path = DATA_DIR / f"{plan_id}.pdf"
    generate_pdf(plan, pdf_path)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO plans (plan_id, payload, created_at) VALUES (?, ?, ?)",
            (plan_id, json.dumps(plan, ensure_ascii=False), datetime.utcnow().isoformat()),
        )

    return {
        "plan": plan,
        "pdf_url": f"/api/plan/{plan_id}/pdf",
    }


@app.get("/api/plan/{plan_id}/pdf")
def get_plan_pdf(plan_id: str) -> FileResponse:
    path = DATA_DIR / f"{plan_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(path, filename=f"workout_plan_{plan_id}.pdf")


app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")
