from __future__ import annotations

from typing import Any


def extract_posture_insights(weight_kg: float, height_cm: float) -> dict[str, Any]:
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
    if bmi < 18.5:
        body_status = "偏瘦，优先提升肌肉量与总热量"
    elif bmi < 24:
        body_status = "体重区间正常，建议精细化增肌或塑形"
    elif bmi < 28:
        body_status = "轻度超重，建议温和减脂+力量训练"
    else:
        body_status = "超重，建议以减脂和关节友好训练为先"

    return {
        "bmi": bmi,
        "body_status": body_status,
        "muscle_weak_points": ["后链力量（臀腿/下背）", "肩胛稳定", "核心抗伸展能力"],
        "posture_compare": {
            "current": "可能存在圆肩、骨盆前倾与胸椎活动受限风险（基于基础模型预估）",
            "target": "头-肩-髋-踝基本在一条线上，躯干稳定，步态更经济",
        },
    }


def daily_macro(weight_kg: float, carb_per_kg: float, protein_per_kg: float) -> dict[str, float]:
    carbs = round(weight_kg * carb_per_kg)
    protein = round(weight_kg * protein_per_kg)
    fat = round((carbs + protein) * 0.24)
    kcal = carbs * 4 + protein * 4 + fat * 9
    return {"carbs_g": carbs, "protein_g": protein, "fat_g": fat, "kcal": kcal}


def meal_grams_from_macro(macro: dict[str, float]) -> dict[str, int]:
    protein = macro["protein_g"]
    carbs = macro["carbs_g"]
    fat = macro["fat_g"]
    return {
        "生肉_g": int(round(protein * 4.8)),
        "米饭(熟)_g": int(round(carbs * 2.2)),
        "绿叶蔬菜_g": 500,
        "鱼油_caps": max(2, int(round(fat / 20))),
    }


def build_strength_cycle_plan(weight_kg: float) -> list[dict[str, Any]]:
    phases = [
        ("第1-16天 高碳", 3.0, 2.0),
        ("第17-23天 中碳", 2.2, 2.0),
        ("第24-30天 低碳", 1.6, 2.0),
    ]
    rows = []
    for name, ckg, pkg in phases:
        macro = daily_macro(weight_kg, ckg, pkg)
        foods = meal_grams_from_macro(macro)
        rows.append({"phase": name, "macro_per_kg": {"carb": ckg, "protein": pkg}, "macro": macro, "foods": foods})
    return rows


def build_non_strength_plan(weight_kg: float) -> list[dict[str, Any]]:
    phases = [
        ("第1-10天 控糖适应", 1.8, 1.6),
        ("第11-20天 稳态减脂", 1.5, 1.6),
        ("第21-30天 维持与回升", 1.8, 1.5),
    ]
    rows = []
    for name, ckg, pkg in phases:
        macro = daily_macro(weight_kg, ckg, pkg)
        foods = meal_grams_from_macro(macro)
        rows.append({"phase": name, "macro_per_kg": {"carb": ckg, "protein": pkg}, "macro": macro, "foods": foods})
    return rows
