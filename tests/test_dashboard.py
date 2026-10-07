"""User-flow regressions using an isolated copy of the checked-in observations."""
import io
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pyarrow.ipc as ipc
import streamlit as st
from streamlit.testing.v1 import AppTest

from housing.db import connect as database_connect

ROOT = Path(__file__).resolve().parents[1]


def isolated_database(_path):
    # No app run, including navigation to records, can write the real database.
    with sqlite3.connect(f"file:{ROOT / 'data/housing.sqlite3'}?mode=ro", uri=True) as source:
        target = database_connect(":memory:")
        source.backup(target)
    return target


def mortgage_gap_database(path):
    # Fixed gap so the missing-month assertions do not depend on later BoC releases.
    db = isolated_database(path)
    db.execute("DELETE FROM observations WHERE series_id='mortgage_uninsured_fixed_5plus' AND period>'2026-06'")
    db.commit()
    return db


def chart_frame(element):
    spec = json.loads(element.proto.spec)
    dataset = next(item for item in element.proto.datasets if item.name == spec["data"]["name"])
    return ipc.open_stream(io.BytesIO(dataset.data.data)).read_all().to_pandas()


def chart_with_column(app, column):
    return next(frame for element in app.get("arrow_vega_lite_chart")
                if column in (frame := chart_frame(element)).columns)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.auth_patch = patch.dict("os.environ", {"HOUSING_REQUIRE_OWNER_AUTH": "0"})
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        self.database_patch = patch("housing.db.connect", side_effect=isolated_database)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assert_clean()

    def assert_clean(self):
        self.assertFalse(list(self.app.exception), [item.message for item in self.app.exception])

    def navigate(self, page):
        self.app.radio(key="navigation").set_value(page).run()
        self.assert_clean()

    def select(self, label, value):
        next(item for item in self.app.selectbox if item.label == label).set_value(value).run()
        self.assert_clean()

    def test_all_pages_and_economic_topics_render_without_writing_observations(self):
        before = sorted((ROOT / "data/observations").glob("*.json"))
        for page in ("租赁市场", "经济与供给", "月供情景", "数据与记录", "市场总览"):
            with self.subTest(page=page):
                self.navigate(page)
        self.navigate("经济与供给")
        self.assertTrue({"利率与融资", "就业", "住宅建设", "人口"}.issubset(
            {item.value for item in self.app.subheader}))
        self.assertEqual(sorted((ROOT / "data/observations").glob("*.json")), before)

    def test_monthly_asking_scope_export_language_and_no_snapshot_backfill(self):
        import re
        self.navigate("租赁市场")
        self.assertEqual(self.app.radio(key="rental-view").value, "月度挂牌租金")
        trend = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        self.assertEqual(trend["period"].max(), "2026-08")
        self.assertEqual(trend["value"].iloc[-1], 2570)
        self.assertEqual(chart_with_column(self.app, "月租金")["月租金"].tolist(), [2229, 2955, 3642])
        with patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.app.selectbox(key="asking-month").set_value("2025-10").run()
        self.assert_clean()
        self.assertEqual(len(self.app.get("arrow_vega_lite_chart")), 1)
        self.assertTrue(any("该月尚无" in item.value for item in self.app.info))
        exported = pd.read_csv(io.BytesIO(next(c for c in downloads.call_args_list if c.args[0] == "下载月度租金与来源").args[1]))
        self.assertEqual(exported["period"].max(), "2025-10")
        self.assertEqual(set(exported["series_id"]), {"toronto_asking_rent_total"})
        self.assertTrue(exported["sha256"].str.len().eq(64).all())
        self.app.selectbox(key="asking-month").set_value("2026-07").run()
        self.app.radio(key="language").set_value("English").run()
        self.assert_clean()
        for kind in ("title", "subheader", "caption", "markdown", "warning", "info"):
            for element in self.app.get(kind):
                self.assertIsNone(re.search(r"[\u4e00-\u9fff]", element.value), element.value)
        self.assertEqual(chart_with_column(self.app, "Monthly rent")["Monthly rent"].tolist(), [2242, 2956, 3655])

    def test_bedroom_monthly_comparison_uses_real_ten_month_history(self):
        self.navigate("租赁市场")
        self.app.selectbox(key="asking-room").set_value("compare").run()
        self.assert_clean()
        trend = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        self.assertEqual(len(trend), 30)
        self.assertEqual(trend["period"].min(), "2025-11")
        self.assertEqual(trend["period"].max(), "2026-08")
        self.assertEqual(trend[trend["指标"] == "一卧"]["value"].tolist(), [2237,2228,2203,2206,2195,2214,2218,2220,2242,2229])
        self.app.selectbox(key="asking-room").set_value("3br").run()
        self.assert_clean()
        trend = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        self.assertEqual(set(trend["指标"]), {"三卧"})
        self.assertEqual(trend["value"].tolist(), [3499,3508,3469,3508,3479,3567,3555,3588,3655,3642])

    def test_markham_backfill_reaches_chart_and_export(self):
        self.navigate("租赁市场")
        self.app.radio(key="rental-view").set_value("地区租金对比").run()
        self.app.selectbox(key="region-False-0").set_value("markham").run()
        self.app.selectbox(key="region-False-1").set_value("none").run()
        with patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.app.selectbox(key="region-False-2").set_value("none").run()
        self.assert_clean()
        trend = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        self.assertEqual(trend['period'].tolist()[:2], ['2025-09', '2025-10'])
        self.assertEqual(trend['value'].tolist()[:2], [2473, 2492])
        self.assertEqual(trend['value'].tolist()[-10:], [2390,2424,2448,2374,2324,2324,2239,2250,2211,2309])
        self.assertTrue(any('实际观测：12 个' in c.value for c in self.app.caption))
        self.assertFalse(any('当前仅有' in w.value for w in self.app.warning))
        export = pd.read_csv(io.BytesIO(next(c for c in downloads.call_args_list if c.args[0]=='下载地区对比数据').args[1]))
        self.assertEqual(export['value'].tolist(), trend['value'].tolist())
        self.assertTrue(export['sha256'].str.len().eq(64).all())

    def test_unavailable_rooms_explain_source_and_offer_same_room_annual(self):
        self.navigate("租赁市场")
        self.app.radio(key="rental-view").set_value("地区租金对比").run()
        self.app.selectbox(key="region-False-0").set_value("markham").run()
        self.app.selectbox(key="region-False-1").set_value("none").run()
        self.app.selectbox(key="region-False-2").set_value("none").run()
        self.app.selectbox(key="region-room-False").set_value("1br").run()
        self.assert_clean()
        self.assertIn('一卧 · 暂无数据', self.app.selectbox(key="region-room-False").options)
        self.assertTrue(any('已核验月度图表未提供' in x.value for x in self.app.info))
        self.assertEqual(len(self.app.get('arrow_vega_lite_chart')), 0)
        self.app.button(key='annual-alternative-markham').click().run()
        self.assert_clean()
        self.assertEqual(self.app.selectbox(key='region-source').value, '年度存量租金（CMHC）')
        self.assertEqual(self.app.selectbox(key='region-True-0').value, 'markham')
        self.assertEqual(self.app.selectbox(key='region-room-True').value, '1br')
        self.assertEqual(len(chart_frame(self.app.get('arrow_vega_lite_chart')[0])), 4)
        self.app.selectbox(key='region-room-True').set_value('studio').run()
        self.assert_clean()
        self.assertTrue(any('均抑制发布' in x.value for x in self.app.info))
        self.assertEqual(len(self.app.get('arrow_vega_lite_chart')), 0)
        self.app.radio(key='language').set_value('English').run()
        self.assert_clean()
        self.assertTrue(any('CMHC suppresses' in x.value for x in self.app.info))

    def test_regional_filters_export_missing_and_annual_scope(self):
        import re
        self.navigate("租赁市场")
        self.app.radio(key="rental-view").set_value("地区租金对比").run()
        self.assert_clean()
        self.app.selectbox(key="region-False-0").set_value("oakville").run()
        self.app.selectbox(key="region-False-1").set_value("none").run()
        self.app.selectbox(key="region-False-2").set_value("none").run()
        with patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.app.selectbox(key="region-room-False").set_value("2br").run()
        self.assert_clean()
        self.assertEqual(self.app.metric[0].value, "$3,034")
        trend = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        self.assertEqual(trend["value"].tolist(), [2584,2629,2656,2820,3034])
        export = pd.read_csv(io.BytesIO(next(c for c in downloads.call_args_list if c.args[0]=="下载地区对比数据").args[1]))
        self.assertEqual(set(export['series_id']), {'regional_asking_oakville_2br'})
        self.app.selectbox(key="region-False-0").set_value("downtown").run()
        self.assert_clean()
        self.assertEqual(len(self.app.get("arrow_vega_lite_chart")),0)
        self.assertTrue(any('Downtown Toronto' in x.value for x in self.app.info))
        self.app.selectbox(key="region-source").set_value("年度存量租金（CMHC）").run()
        self.app.selectbox(key="region-True-0").set_value("richmond_vaughan_king").run()
        self.app.selectbox(key="region-measure").set_value("vacancy").run()
        self.assert_clean()
        self.app.radio(key="language").set_value("English").run()
        self.assert_clean()
        for kind in ('subheader','caption','info','warning','markdown'):
            for e in self.app.get(kind):
                self.assertIsNone(re.search(r'[\u4e00-\u9fff]', e.value), e.value)
        self.assertTrue(all(m.value.endswith('%') or m.value=='—' for m in self.app.metric))

    def test_rental_all_five_room_categories_reconcile_to_both_official_years(self):
        self.navigate("租赁市场")
        self.app.radio(key="rental-view").set_value("年度存量租金（CMHC）").run()
        expected = {
            "2022": ([1306, 1527, 1779, 2041, 1660], [2285, 2194, 2692, 2969, 2547]),
            "2023": ([1414, 1691, 1961, 2191, 1826], [2279, 2399, 2890, 3148, 2726]),
            "2025": ([1491, 1761, 2046, 2317, 1913], [2242, 2350, 2891, 3306, 2747]),
            "2024": ([1448, 1715, 1974, 2225, 1850], [2486, 2365, 2924, 3255, 2758]),
        }
        for year, (pbr, condo) in expected.items():
            with self.subTest(year=year), patch.object(st, "download_button", wraps=st.download_button) as downloads:
                self.app.selectbox(key="rental-year").set_value(year).run()
                self.assert_clean()
                table = next(item.value for item in self.app.dataframe
                             if "专建出租公寓（加元/月）" in item.value.columns)
                self.assertEqual(table["房型"].tolist(), ["开间", "一卧", "两卧", "三卧及以上", "公寓全部卧室类型"])
                self.assertEqual(table["专建出租公寓（加元/月）"].tolist(), pbr)
                self.assertEqual(table["业主出租 condo（加元/月）"].tolist(), condo)
                bars = chart_with_column(self.app, "月租金")
                self.assertEqual(len(bars), 10)
                self.assertEqual(bars[bars["市场"] == "专建出租公寓"]["月租金"].tolist(), pbr)
                self.assertEqual(bars[bars["市场"] == "业主出租 condo"]["月租金"].tolist(), condo)
                rental_download = next(call for call in downloads.call_args_list if call.args[0] == "下载房型租金对照")
                exported = pd.read_csv(io.BytesIO(rental_download.args[1]))
                self.assertEqual(exported["调查年份"].tolist(), [int(year)] * 10)
                self.assertEqual(exported[exported["市场"] == "专建出租公寓"]["月租金"].tolist(), pbr)
                self.assertEqual(exported[exported["市场"] == "业主出租 condo"]["月租金"].tolist(), condo)
                self.assertTrue(exported["来源文件"].notna().all())
                self.assertTrue(exported["来源表"].notna().all())
                self.assertTrue(exported["单元格"].notna().all())
                if year == "2024":
                    self.assertFalse((table["专建出租公寓均值较上年"] == "无上年可比值").any())
                if year == "2022":
                    self.assertTrue((table["专建出租公寓均值较上年"] == "无上年可比值").all())

    def test_rental_history_and_sales_heatmap_follow_selected_period(self):
        self.app.selectbox(key="market-month").set_value("2025-08").run()
        self.app.selectbox(key="market-window").set_value("近 12 个月").run()
        heatmap = chart_with_column(self.app, "年份")
        self.assertEqual(heatmap["所属期"].min(), "2024-09")
        self.assertEqual(heatmap["所属期"].max(), "2025-08")
        self.assertEqual(heatmap.loc[heatmap["所属期"] == "2025-08", "成交量"].iloc[0], 5211)
        self.navigate("租赁市场")
        self.app.radio(key="rental-view").set_value("年度存量租金（CMHC）").run()
        self.app.selectbox(key="rental-year").set_value("2023").run()
        self.app.selectbox(key="rental-trend-room").set_value("2br").run()
        trend = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        self.assertEqual(set(trend["period"]), {"2022", "2023"})
        self.assertEqual(trend[trend["指标"] == "专建出租公寓"]["value"].tolist(), [1779, 1961])
        self.assertEqual(trend[trend["指标"] == "业主出租 condo"]["value"].tolist(), [2692, 2890])
        history = self.app.dataframe[0].value
        self.assertTrue(history["来源文件"].str.contains("2023").all())
        self.assertTrue(history["质量等级"].notna().all())
        self.app.selectbox(key="rental-year").set_value("2022").run()
        spec = json.loads(self.app.get("arrow_vega_lite_chart")[0].proto.spec)
        self.assertTrue(spec["mark"]["point"])  # A single survey must still be visible.

    def test_mortgage_missing_month_remains_missing_in_card_chart_and_source(self):
        with patch("housing.db.connect", side_effect=mortgage_gap_database):
            self.navigate("经济与供给")
            self.app.selectbox(key="context-rates-month").set_value("2026-08").run()
            self.app.selectbox(key="trend-field-rates").set_value("mortgage_uninsured_fixed_5plus").run()
        markup = "".join(item.proto.body for item in self.app.get("html") if "metric-grid" in item.proto.body and not item.proto.body.startswith("<style>"))
        self.assertIn("新增固定按揭利率", markup)
        self.assertIn("暂无数据", markup)
        self.assertIn("2026年8月尚无观测", markup)
        self.assertNotIn("4.35%", markup)
        self.assertTrue(any("2026年6月，4.35%" in item.value for item in self.app.warning))
        table = self.app.dataframe[0].value.set_index("所属月份")
        mortgage_column = next(column for column in table if column.startswith("新增固定按揭利率"))
        self.assertEqual(table.loc["2026-06", mortgage_column], 4.35)
        self.assertTrue(pd.isna(table.loc["2026-07", mortgage_column]))
        self.assertTrue(pd.isna(table.loc["2026-08", mortgage_column]))
        chart = chart_frame(self.app.get("arrow_vega_lite_chart")[0]).set_index("period")
        self.assertEqual(chart.loc["2026-06", "value"], 4.35)
        self.assertTrue(pd.isna(chart.loc["2026-07", "value"]))
        self.assertTrue(pd.isna(chart.loc["2026-08", "value"]))
        scale = json.loads(self.app.get("arrow_vega_lite_chart")[0].proto.spec)["encoding"]["x"]["scale"]
        self.assertEqual(scale["type"], "utc")
        self.assertEqual(scale["domain"][-1], "2026-08-01")

    def test_missing_rental_room_stays_explicit_in_table_and_export(self):
        def without_condo_three_bedrooms(path):
            db = isolated_database(path)
            db.execute("DELETE FROM observations WHERE series_id=? AND period=?",
                       ("toronto_condo_rent_3plus", "2025"))
            db.commit()
            return db

        with patch("housing.db.connect", side_effect=without_condo_three_bedrooms), \
                patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.navigate("租赁市场")
            self.app.radio(key="rental-view").set_value("年度存量租金（CMHC）").run()
        table = next(item.value for item in self.app.dataframe
                     if "专建出租公寓（加元/月）" in item.value.columns).set_index("房型")
        self.assertTrue(pd.isna(table.loc["三卧及以上", "业主出租 condo（加元/月）"]))
        self.assertEqual(table.loc["三卧及以上", "业主出租 condo均值较上年"], "本期无观测")
        bars = chart_with_column(self.app, "月租金")
        self.assertEqual(len(bars), 9)
        self.assertFalse(((bars["房型"] == "三卧及以上") & (bars["市场"] == "业主出租 condo")).any())
        download = next(call for call in downloads.call_args_list if call.args[0] == "下载房型租金对照")
        exported = pd.read_csv(io.BytesIO(download.args[1]))
        self.assertEqual(len(exported), 10)
        missing = exported[(exported["房型"] == "三卧及以上") & (exported["市场"] == "业主出租 condo")].iloc[0]
        self.assertTrue(pd.isna(missing["月租金"]))
        self.assertEqual(missing["状态"], "no_observation")

    def test_comparison_rate_survives_editing_scenario_rate(self):
        self.navigate("月供情景")
        self.app.number_input(key="comparison-rate").set_value(6.25).run()
        self.app.number_input(key="scenario-rate").set_value(4.0).run()
        self.assert_clean()
        self.assertEqual(self.app.number_input(key="comparison-rate").value, 6.25)
        self.assertEqual(self.app.number_input(key="scenario-rate").value, 4.0)
        self.app.number_input(key="principal").set_value(700_000).run()
        self.navigate("市场总览")
        self.navigate("月供情景")
        self.assertEqual(self.app.number_input(key="principal").value, 700_000)
        self.assertEqual(self.app.number_input(key="comparison-rate").value, 6.25)
        self.assertEqual(self.app.number_input(key="scenario-rate").value, 4.0)
        self.app.number_input(key="principal").set_value(0).run()
        self.assert_clean()
        self.assertEqual([metric.value for metric in self.app.metric], ["$0.00", "$0.00"])

    def test_mortgage_chart_matches_inputs_and_blank_is_not_zero(self):
        from housing.affordability import monthly_payment
        self.navigate("月供情景")
        self.app.number_input(key="principal").set_value(650_000).run()
        self.assert_clean()
        values = chart_with_column(self.app, "月供")["月供"].tolist()
        rates = [self.app.number_input(key=k).value for k in ("scenario-rate", "comparison-rate")]
        self.assertEqual(values, [monthly_payment(650_000, rate, 25) for rate in rates])
        self.app.number_input(key="principal").set_value(None).run()
        self.assert_clean()
        self.assertTrue(any("请填写全部" in message.value for message in self.app.info))
        self.assertFalse(self.app.get("arrow_vega_lite_chart"))
        self.app.number_input(key="principal").set_value(0).run()
        self.assert_clean()
        self.assertEqual(chart_with_column(self.app, "月供")["月供"].tolist(), [0, 0])

    def test_source_status_distinguishes_withheld_values_from_late_updates(self):
        from housing.catalog import SERIES
        with patch("housing.db.connect", side_effect=mortgage_gap_database):
            self.navigate("数据与记录")
        table = self.app.dataframe[0].value
        withheld = table[table["状态"] == "来源抑制发布"]
        self.assertEqual(len(withheld), 11)
        self.assertTrue(withheld["应有所属期"].eq("2025").all())
        mortgage = table[table["指标"] == SERIES["mortgage_uninsured_fixed_5plus"][0]].iloc[0]
        self.assertEqual(mortgage["状态"], "超过保守检查日")
        self.assertEqual(mortgage["最近所属期"], "2026-06")
        self.app.radio(key="language").set_value("English").run()
        self.assert_clean()
        translated = self.app.dataframe[0].value
        self.assertEqual((translated["Status"] == "Withheld by source").sum(), 11)

    def test_record_save_open_and_download_in_isolated_workspace(self):
        import shutil
        import tempfile
        from housing.snapshot import open_snapshot
        before = sorted((ROOT / "data/observations").glob("*.json"))
        with tempfile.TemporaryDirectory(prefix="housing-record-flow-") as folder:
            root = Path(folder)
            shutil.copy2(ROOT / "app.py", root / "app.py")
            (root / "src").symlink_to(ROOT / "src", target_is_directory=True)
            (root / "data").mkdir()
            (root / "data/housing.sqlite3").touch()  # connect is patched to an in-memory copy.
            (root / "data/observations").mkdir()
            self.app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
            self.navigate("数据与记录")
            self.select("记录月份", "2025-08")
            with patch.object(st, "download_button", wraps=st.download_button) as downloads:
                next(b for b in self.app.button if b.label == "保存本地记录").click().run()
            self.assert_clean()
            saved = list((root / "data/observations").glob("*.json"))
            self.assertEqual(len(saved), 1)
            record = open_snapshot(saved[0])
            self.assertEqual(record["period"], "2025-08")
            self.assertTrue(record["inputs"]["trreb_sales"]["versions"])
            payload = next(c.args[1] for c in downloads.call_args_list if c.args[0] == "下载这份记录")
            self.assertEqual(json.loads(payload), record)
            self.assertEqual(next(w for w in self.app.selectbox if w.label == "打开既有记录").value.resolve(), saved[0].resolve())
            next(b for b in self.app.button if b.label == "保存本地记录").click().run()
            self.assert_clean()
            self.assertEqual(len(list((root / "data/observations").glob("*.json"))), 2)
            self.assertEqual(open_snapshot(saved[0]), record)
        self.assertEqual(sorted((ROOT / "data/observations").glob("*.json")), before)

    def test_market_month_and_window_scope_cards_chart_and_csv_together(self):
        self.app.selectbox(key="market-month").set_value("2025-08").run()
        with patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.app.selectbox(key="market-window").set_value("近 12 个月").run()
        self.assert_clean()
        table = self.app.dataframe[0].value
        self.assertEqual(len(table), 12)
        self.assertEqual(table["所属月份"].iloc[0], "2024-09")
        self.assertEqual(table["所属月份"].iloc[-1], "2025-08")
        sales_column = next(column for column in table if column.startswith("成交量"))
        self.assertEqual(table[sales_column].iloc[-1], 5211)
        markup = "".join(item.proto.body for item in self.app.get("html"))
        self.assertIn("5,211", markup)
        self.assertIn("$969,700", markup)
        chart = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        self.assertEqual(chart["period"].min(), "2024-09")
        self.assertEqual(chart["period"].max(), "2025-08")
        price_column = next(column for column in table if column.startswith("HPI 综合基准房价"))
        self.assertEqual(chart["value"].tolist(), table[price_column].tolist())
        sales_chart = chart_frame(self.app.get("arrow_vega_lite_chart")[1])
        self.assertEqual(sales_chart[sales_chart["指标"] == "成交量"]["value"].tolist(), table[sales_column].tolist())
        download = next(call for call in downloads.call_args_list if call.kwargs.get("key") == "download-trreb")
        exported = pd.read_csv(io.BytesIO(download.args[1]))
        pd.testing.assert_frame_equal(exported, table, check_dtype=False)
        self.assertEqual(download.args[2], "trreb-2024-09-2025-08.csv")

    def test_language_switch_preserves_filters_inputs_and_export_values(self):
        self.app.selectbox(key="market-month").set_value("2025-08").run()
        self.app.selectbox(key="market-window").set_value("近 12 个月").run()
        chinese = self.app.dataframe[0].value
        with patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.app.radio(key="language").set_value("English").run()
        self.assert_clean()
        self.assertEqual(self.app.title[0].value, "Market overview")
        self.assertEqual(self.app.selectbox(key="market-month").value, "2025-08")
        self.assertEqual(self.app.selectbox(key="market-window").value, "近 12 个月")
        english = self.app.dataframe[0].value
        self.assertEqual(english.values.tolist(), chinese.values.tolist())
        exported = next(call for call in downloads.call_args_list if call.kwargs.get("key") == "download-trreb")
        pd.testing.assert_frame_equal(pd.read_csv(io.BytesIO(exported.args[1])), english, check_dtype=False)
        self.navigate("月供情景")
        self.app.number_input(key="principal").set_value(700_000).run()
        self.app.number_input(key="comparison-rate").set_value(6.25).run()
        payments = [m.value for m in self.app.metric]
        self.app.radio(key="language").set_value("中文").run()
        self.assertEqual(self.app.title[0].value, "月供情景")
        self.assertEqual(self.app.number_input(key="principal").value, 700_000)
        self.assertEqual(self.app.number_input(key="comparison-rate").value, 6.25)
        self.assertEqual([m.value for m in self.app.metric], payments)

    def test_language_switch_retains_chart_data_with_reference_transformer(self):
        import altair as alt
        original = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        # A host transformer may serialize data as a reference, not inline rows.
        # Language changes must retain the actual data independently of that context.
        alt.data_transformers.register("reference_only_test", lambda data: {"name": "external-data"})
        with alt.data_transformers.enable("reference_only_test"):
            self.app.radio(key="language").set_value("English").run()
            self.assert_clean()
            translated = chart_frame(self.app.get("arrow_vega_lite_chart")[0])
        pd.testing.assert_frame_equal(original[["period", "value"]], translated[["period", "value"]])

    def test_english_pages_have_translated_text_and_nonempty_bound_chart_data(self):
        import re
        self.app.radio(key="language").set_value("English").run()
        for page in ("市场总览", "租赁市场", "经济与供给", "月供情景", "数据与记录"):
            self.navigate(page)
            if page == "租赁市场":
                self.app.radio(key="rental-view").set_value("年度存量租金（CMHC）").run()
            for _ in (None,):
                self.assert_clean()
                for kind in ("title", "subheader", "caption", "markdown", "warning", "info"):
                    for element in self.app.get(kind):
                        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", element.value), element.value)
                for element in self.app.get("arrow_vega_lite_chart"):
                    spec = json.loads(element.proto.spec)
                    values = chart_frame(element)
                    self.assertFalse(values.empty)
                    for encoding in spec["encoding"].values():
                        for entry in encoding if isinstance(encoding, list) else [encoding]:
                            if "field" in entry:
                                self.assertIn(entry["field"], values.columns)
                    self.assertIsNone(re.search(r"[\u4e00-\u9fff]", str(values.columns.tolist())))
                if page == "租赁市场":
                    rents = chart_with_column(self.app, "Monthly rent")
                    self.assertEqual(rents["Monthly rent"].tolist(), [1491, 2242, 1761, 2350, 2046, 2891, 2317, 3306, 1913, 2747])


if __name__ == "__main__":
    unittest.main()
