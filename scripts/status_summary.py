"""Print current data counts as Markdown, so handoff notes need not copy numbers that go stale."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from housing.catalog import SERIES

KEY_SERIES = ("trreb_sales", "trreb_hpi_benchmark", "toronto_asking_rent_total", "gta_condo_lease_rent_1br",
              "mortgage_uninsured_fixed_5plus", "toronto_unemployment_rate", "toronto_cma_2011_starts",
              "toronto_cmhc_unabsorbed_inventory", "toronto_starts_condo", "toronto_cma_2021_population")


def summary(root=ROOT):
    db = sqlite3.connect(f"file:{root / 'data/housing.sqlite3'}?mode=ro", uri=True)
    try:
        one = lambda sql: db.execute(sql).fetchone()[0]
        lines = ["| 项目 | 当前值 |", "| --- | --- |",
                 f"| 含版本观测 | {one('SELECT COUNT(*) FROM observations'):,} |",
                 f"| 有数值系列／登记系列 | {one('SELECT COUNT(DISTINCT series_id) FROM observations')}／{len(SERIES)} |",
                 f"| 登记原件 | {one('SELECT COUNT(*) FROM raw_files'):,} |",
                 f"| 地区转售记录（含版本） | {one('SELECT COUNT(*) FROM district_observations'):,} |"]
        for series_id in KEY_SERIES:
            first, last, count = db.execute("SELECT MIN(period), MAX(period), COUNT(DISTINCT period) FROM observations "
                                            "WHERE series_id=?", (series_id,)).fetchone()
            lines.append(f"| {SERIES[series_id][0]} | {first}—{last}，{count} 期 |" if count
                         else f"| {SERIES[series_id][0]} | 暂无 |")
    finally:
        db.close()
    reports = sorted((root / "data/run_reports").glob("official-*.json"))
    if reports:
        latest = json.loads(reports[-1].read_text())
        state = "成功发布" if latest.get("snapshot_published") else f"未发布：{latest.get('error', '见报告')}"
        lines.append(f"| 最近定时周期 | {latest.get('started_at', '')[:16]}，{state} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary())
