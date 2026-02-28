from app.planner import daily_macro, build_strength_cycle_plan, build_non_strength_plan


def test_daily_macro_formula():
    out = daily_macro(80, 2.5, 2.0)
    assert out["carbs_g"] == 200
    assert out["protein_g"] == 160
    assert out["fat_g"] == 86


def test_strength_plan_has_three_phases():
    plan = build_strength_cycle_plan(88)
    assert len(plan) == 3
    assert plan[0]["macro"]["carbs_g"] > plan[-1]["macro"]["carbs_g"]


def test_non_strength_plan_has_three_phases():
    plan = build_non_strength_plan(60)
    assert len(plan) == 3
