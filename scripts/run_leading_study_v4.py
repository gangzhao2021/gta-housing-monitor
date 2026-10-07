"""Run protocol v4 and write data/research/v4-report.json (private)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing import leading, leading_v3

PROTOCOL = json.loads((ROOT / "src/housing/research_protocol_v4.json").read_text())


def main():
    data = leading_v3.load_trreb(ROOT / "data/research/trreb-history.csv", leading.load(ROOT / "data/research/v2-inputs.csv"))
    last_index = max(p for p, r in data["trreb"].items() if r.get("hpi_index") not in (None, ""))
    current = leading.shift(datetime.now().strftime("%Y-%m"), -1)  # last complete month
    report = {"protocol": PROTOCOL["version"], "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "last_target_month": last_index, "current_decision": current, "horizons": {}}
    (first_sub, second_sub) = PROTOCOL["sample"]["subperiods"]
    for h in PROTOCOL["target"]["horizons_months"]:
        last_matured = leading.shift(last_index, 1 - h)
        decisions = leading.months("2006-01", current)
        rows = leading.forecasts(data, h, decisions, PROTOCOL["sample"]["minimum_training_observations"],
                                 features=leading_v3.FEATURES, feature_fn=leading_v3.feature,
                                 target_fn=leading_v3.hpi_target)
        models = {}
        for model in leading_v3.FEATURES + ["combination"]:
            full = leading.evaluate(rows, model, h, PROTOCOL["sample"]["oos_start"], last_matured)
            a = leading.evaluate(rows, model, h, *first_sub)
            b = leading.evaluate(rows, model, h, second_sub[0], last_matured)
            evidence = all(r.get("oos_r2", -1) > 0 for r in (full, a, b)) and (full.get("clark_west_p_one_sided") or 1) < 0.05
            models[model] = {"full": full, first_sub[0] + "/" + first_sub[1]: a, second_sub[0] + "/" + last_matured: b,
                             "evidence": evidence}
        latest = rows.get(current, {})
        report["horizons"][str(h)] = {
            "last_matured_decision": last_matured, "models": models,
            "current_forecasts_research_only": {k: round(v, 2) for k, v in latest.items() if k != "actual" and v is not None},
        }
    output = ROOT / "data/research/v4-report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    output.chmod(0o600)
    for h, part in report["horizons"].items():
        print(f"\n== h={h} months (OOS {PROTOCOL["sample"]["oos_start"]}..{part['last_matured_decision']})")
        print(f"{'model':30s} {'n':>4s} {'R2':>7s} {'R2 10s':>7s} {'R2 20s':>7s} {'CW p':>6s} {'hit':>5s} {'hit bm':>6s} evidence")
        for model, r in part["models"].items():
            full = r["full"]; subs = [v for k, v in r.items() if "/" in k]
            if "oos_r2" not in full:
                print(f"{model:30s} {full['n']:4d} too few cases"); continue
            print(f"{model:30s} {full['n']:4d} {full['oos_r2']:7.3f} {subs[0].get('oos_r2', float('nan')):7.3f} "
                  f"{subs[1].get('oos_r2', float('nan')):7.3f} {full['clark_west_p_one_sided']:6.3f} "
                  f"{full['direction_hit']:5.2f} {full['direction_hit_benchmark']:6.2f} {'YES' if r['evidence'] else 'no'}")
        print("current (research only):", part["current_forecasts_research_only"])


if __name__ == "__main__":
    main()
