"""Definitions selected from the first verified official source samples."""

SERIES = {
    "boc_policy_rate": ("央行隔夜目标利率", "BoC", "V39079", "Canada", "%", "daily", "not adjusted", "none", "按生效日公布；月末值为最后一个有效日"),
    "goc_5y_yield": ("五年政府基准债收益率", "BoC", "BD.CDN.5YR.DQ.YLD", "Canada", "%", "daily", "not adjusted", "none", "交易日收盘收益率；月图为有效日均值"),
    "mortgage_uninsured_fixed_5plus": ("新增放款非受保固定按揭：五年及以上", "BoC", "V122667786", "Canada", "%", "monthly", "not adjusted", "none", "特许银行金额加权均值；包括续贷和再融资"),
    "toronto_unemployment_rate": ("Toronto CMA 失业率", "StatsCan", "v1642720028", "Toronto CMA 2021 boundary", "%", "monthly", "seasonally adjusted", "none", "14-10-0460-01；单月季调估计"),
    "toronto_employment_rate": ("Toronto CMA 就业率", "StatsCan", "v1642720044", "Toronto CMA 2021 boundary", "%", "monthly", "seasonally adjusted", "none", "14-10-0460-01；单月季调估计"),
    "toronto_participation_rate": ("Toronto CMA 参与率", "StatsCan", "v1642720036", "Toronto CMA 2021 boundary", "%", "monthly", "seasonally adjusted", "none", "14-10-0460-01；单月季调估计"),
    "trreb_sales": ("转售成交", "TRREB", "Market Watch p3", "All TRREB Areas", "sales", "monthly", "not adjusted", "none", "当月报告成交；全房型"),
    "trreb_new_listings": ("新增挂牌", "TRREB", "Market Watch p3", "All TRREB Areas", "listings", "monthly", "not adjusted", "none", "当月进入 MLS 的新挂牌"),
    "trreb_active_listings": ("月末有效挂牌", "TRREB", "Market Watch p3", "All TRREB Areas", "listings", "monthly", "not adjusted", "none", "月末存量"),
    "trreb_hpi_composite": ("MLS HPI 综合指数", "TRREB", "Market Watch p25", "All TRREB Areas", "index", "monthly", "not adjusted", "none", "综合指数，与 benchmark price 分开"),
    "trreb_hpi_benchmark": ("MLS HPI 综合基准房价", "TRREB", "Market Watch p25", "All TRREB Areas", "CAD", "monthly", "not adjusted", "none", "综合 benchmark price，非平均成交价"),
    "toronto_cma_2011_starts": ("住宅开工", "StatsCan", "34-10-0154-01", "Toronto CMA 2011 boundary", "units", "monthly", "actual, not SAAR", "none", "CMHC Starts and Completions Survey；Total units"),
    "toronto_cma_2011_completions": ("住宅竣工", "StatsCan", "34-10-0154-01", "Toronto CMA 2011 boundary", "units", "monthly", "actual", "none", "CMHC Starts and Completions Survey；Total units"),
    "toronto_cma_2011_under_construction": ("在建住宅", "StatsCan", "34-10-0154-01", "Toronto CMA 2011 boundary", "units", "monthly", "stock", "none", "CMHC Starts and Completions Survey；月末存量，Total units"),
    "toronto_cma_2021_population": ("Toronto CMA 人口估计", "StatsCan", "17-10-0148-01", "Toronto CMA 2021 boundary", "persons", "annual", "July 1 estimate", "none", "Total gender、All ages；年度值不插值为月度值"),
    "wti_cushing_spot_price": ("WTI 原油现货月均价", "EIA", "RWTC monthly", "Cushing, Oklahoma", "USD/barrel", "monthly", "not adjusted", "none", "美国 WTI 现货月均价；国际能源背景，不等于 Ontario 零售能源或 GTA 建筑成本；尚未验证房价预测增量价值"),
    "usd_cad_monthly": ("美元兑加元月均汇率", "BoC FX", "FXMUSDCAD", "Canada", "CAD/USD", "monthly", "monthly average", "none", "1 美元兑换的加元数；上升代表加元相对美元走弱，不直接表示 GTA 外国买家需求"),
    "boc_energy_price_index": ("加拿大央行能源商品价格指数", "BoC BCPI", "M.ENER", "Canada", "index", "monthly", "not adjusted", "none", "加拿大商品价格指数能源组；不是 WTI 或本地能源账单。底层缺源时可能沿用前值，后续会修订"),
    "toronto_residential_construction_cost_index": ("Toronto 住宅建筑造价指数", "StatsCan BCPI", "18-10-0289-01 v1617912612", "Toronto CMA 2021 boundary", "index", "quarterly", "2023=100", "none", "住宅建筑 Division composite 报价指数；季度以首月登记，非地价、融资成本或转售房价"),
    "ontario_net_interprovincial_migration": ("Ontario 省际净迁移", "StatsCan Ontario migration", "17-10-0020-01 v509048-v509063", "Ontario", "persons", "quarterly", "not adjusted", "none", "迁入减迁出；季度以首月登记，可为负值；不是 Toronto CMA 人口需求"),
    "ontario_net_international_migration": ("Ontario 国际净迁移", "StatsCan Ontario migration", "17-10-0040-01 v29850372+v29850376-v1566834794", "Ontario", "persons", "quarterly", "not adjusted", "none", "移民+非永久居民净变化-净移出；季度以首月登记，可为负值；不是 Toronto CMA 人口需求"),
}


# Apartment markets remain separate; total rents are source-weighted published
# averages, not an arithmetic mean of the bedroom categories.
RENTAL_BEDROOMS = {
    "studio": "单间 Studio", "1br": "一卧", "2br": "两卧",
    "3plus": "三卧及以上", "total": "公寓全部卧室类型",
}
for market, market_label, rent_table in (
    ("pbr", "专建出租公寓", "1.1.2"),
    ("condo", "出租公寓产权房", "4.1.3"),
):
    for bedroom, bedroom_label in RENTAL_BEDROOMS.items():
        SERIES[f"toronto_{market}_rent_{bedroom}"] = (
            f"{market_label}平均租金 · {bedroom_label}", "CMHC",
            f"Rental Market Survey Table {rent_table}", "Toronto CMA 2021 boundary",
            "CAD/month", "annual", "October survey", "none",
            ("私人出租公寓（3+ 套）" if market == "pbr" else "Condominium Apartment Survey；次级出租市场")
            + f"；{bedroom_label}；平均租金，非当前挂牌租金；均值变化不等于同样本租金涨幅",
        )
    vacancy_types = RENTAL_BEDROOMS if market == "pbr" else {"total": "公寓全部卧室类型"}
    if market == "pbr":
        for bedroom, bedroom_label in RENTAL_BEDROOMS.items():
            SERIES[f"toronto_row_rent_{bedroom}"] = (
                f"专建出租镇屋平均租金 · {bedroom_label.replace('公寓', '镇屋')}", "CMHC",
                "Rental Market Survey Table 2.1.2", "Toronto CMA 2021 boundary",
                "CAD/month", "annual", "October survey", "none",
                f"私人出租镇屋（row / townhouse，3+ 套的出租项目）；{bedroom_label}；平均租金，非当前挂牌租金；均值变化不等于同样本租金涨幅",
            )
    for bedroom, bedroom_label in vacancy_types.items():
        suffix = "rate" if bedroom == "total" else bedroom
        SERIES[f"toronto_{market}_vacancy_{suffix}"] = (
            f"{market_label}空置率 · {bedroom_label}", "CMHC",
            "Rental Market Survey Table " + ("1.1.1" if market == "pbr" else "4.1.1"),
            "Toronto CMA 2021 boundary", "%", "annual", "October survey", "none",
            ("私人出租公寓（3+ 套）" if market == "pbr" else "Condominium Apartment Survey；独立于专建出租公寓")
            + f"；年度 10 月调查；{bedroom_label}",
        )

SOURCE_URLS = {
    "BoC": "https://www.bankofcanada.ca/valet/",
    "StatsCan": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046001",
    "TRREB": "https://trreb.ca/market-data/market-watch/",
}

SERIES_URLS = {
    "boc_policy_rate": "https://www.bankofcanada.ca/valet-api-how-to/",
    "goc_5y_yield": "https://www.bankofcanada.ca/rates/interest-rates/canadian-bonds/",
    "mortgage_uninsured_fixed_5plus": "https://www.bankofcanada.ca/rates/banking-and-financial-statistics/interest-rates-for-new-and-existing-lending-by-chartered-banks/",
    "toronto_unemployment_rate": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046001",
    "toronto_employment_rate": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046001",
    "toronto_participation_rate": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046001",
    "trreb_sales": "https://trreb.ca/market-data/market-watch/market-watch-archive/",
    "trreb_new_listings": "https://trreb.ca/market-data/market-watch/market-watch-archive/",
    "trreb_active_listings": "https://trreb.ca/market-data/market-watch/market-watch-archive/",
    "trreb_hpi_composite": "https://trreb.ca/market-data/market-watch/market-watch-archive/",
    "trreb_hpi_benchmark": "https://trreb.ca/market-data/market-watch/market-watch-archive/",
    "toronto_cma_2011_starts": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410015401",
    "toronto_cma_2011_completions": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410015401",
    "toronto_cma_2011_under_construction": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3410015401",
    "toronto_cma_2021_population": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710014801",
    "wti_cushing_spot_price": "https://www.eia.gov/dnav/pet/hist/rwtcm.htm",
    "usd_cad_monthly": "https://www.bankofcanada.ca/rates/exchange/monthly-exchange-rates/",
    "boc_energy_price_index": "https://www.bankofcanada.ca/rates/price-indexes/bcpi/",
    "toronto_residential_construction_cost_index": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810028901",
    "ontario_net_interprovincial_migration": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710002001",
    "ontario_net_international_migration": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710004001",
}

CMHC_RENTAL_URL = "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market/rental-market-report-data-tables"
SERIES_URLS.update({series_id: CMHC_RENTAL_URL for series_id, definition in SERIES.items()
                    if definition[1] == "CMHC"})


ASKING_ROOMS = {"total": "公寓全部卧室类型", "1br": "一卧", "2br": "两卧", "3br": "三卧"}
RENTALS_URL = "https://rentals.ca/blog/canada-national-rent-reports"
for room, name in ASKING_ROOMS.items():
    field = f"toronto_asking_rent_{room}"
    SERIES[field] = (
        f"挂牌租金 · {name}", "Rentals.ca / Urbanation", "Public Datawrapper report dataset",
        "Toronto (Rentals.ca market definition)", "CAD/month", "monthly", "not adjusted", "none",
        "专建出租公寓与 condo 的平均挂牌租金；非签约租金。Toronto 为来源市场名称，不能直接等同 Toronto CMA 或 TRREB 全市场。均值受挂牌构成影响；三卧不等于三卧及以上。",
    )
    SERIES_URLS[field] = RENTALS_URL

from .regions import MONTHLY_REGIONS, CMHC_REGIONS, asking_id, cmhc_id
for region, name in MONTHLY_REGIONS.items():
    if region == 'toronto':
        continue
    for room in (('total',) if region == 'markham' else ('total', '1br', '2br')):
        field = asking_id(region, room)
        SERIES[field] = (f'{name} · {ASKING_ROOMS[room]}', 'Rentals.ca / Urbanation',
            'Top 25 apartment/condo ranking' if room == 'total' else 'Public apartment/condo city table', f'{name} (Rentals.ca market definition)',
            'CAD/month', 'monthly', 'not adjusted', 'none',
            '专建出租公寓与 condo 平均挂牌租金；地区采用来源名称，不合并行政边界；非实际签约租金。')
        SERIES_URLS[field] = RENTALS_URL
for region, name in CMHC_REGIONS.items():
    for measure in ('rent', 'vacancy'):
        for room, room_name in RENTAL_BEDROOMS.items():
            field = cmhc_id(region, measure, room)
            SERIES[field] = (f'{name} · {room_name} · ' + ('平均租金' if measure == 'rent' else '空置率'),
                'CMHC', 'Rental Market Survey Table ' + ('1.1.2' if measure == 'rent' else '1.1.1'),
                name + ' (CMHC 2021 zones)', 'CAD/month' if measure == 'rent' else '%',
                'annual', 'October survey', 'none',
                '专建出租公寓；沿用 CMHC 原始调查分区，组合地区不可当作其中单一城市。')
            SERIES_URLS[field] = CMHC_RENTAL_URL


# Additional background series have independent provenance and are owner-only.
from .background_series import CONFIG as BACKGROUND_CONFIG, url_for
for config in BACKGROUND_CONFIG.values():
    SERIES[config['id']] = (config['label'], config['source'], str(config['vector']),
        config['geo'], config['unit'], 'monthly', 'not adjusted', 'none', config['definition'])
    SERIES_URLS[config['id']] = url_for(config)

from .trreb_yoy import DEFINITION as YOY_DEFINITION, SERIES as YOY_SERIES
for series_id, label in YOY_SERIES.items():
    SERIES[series_id] = (label, 'TRREB', 'Market Watch front page / HPI page', 'All TRREB Areas', '%',
                         'monthly', 'not adjusted', 'none', YOY_DEFINITION)
    SERIES_URLS[series_id] = 'https://trreb.ca/market-data/market-watch/market-watch-archive/'

from .trreb_price_bands import BANDS as PRICE_BANDS, DEFINITION as BAND_DEFINITION
for series_id, (label, _) in PRICE_BANDS.items():
    SERIES[series_id] = (label, 'TRREB', 'Market Watch page 2', 'All TRREB Areas', 'sales',
                         'monthly', 'not adjusted', 'none', BAND_DEFINITION)
    SERIES_URLS[series_id] = 'https://trreb.ca/market-data/market-watch/market-watch-archive/'

from .teranet import GEO as TERANET_GEO, NOTE as TERANET_NOTE, SERIES as TERANET_SERIES, URL as TERANET_URL
for series_id, (label, unit, _) in TERANET_SERIES.items():
    SERIES[series_id] = (label, 'Teranet-National Bank HPI', 'housepriceindex.ca on_toronto', TERANET_GEO, unit,
                         'monthly', 'SA' if series_id.endswith('_sa') else 'not adjusted', 'none', TERANET_NOTE)
    SERIES_URLS[series_id] = TERANET_URL

from .cba_arrears import DEFINITION as ARREARS_DEFINITION, PAGE as ARREARS_PAGE, SERIES as ARREARS_SERIES
for series_id, (label, unit) in ARREARS_SERIES.items():
    SERIES[series_id] = (label, 'CBA mortgage arrears', 'CBA residential mortgages in arrears, Ontario', 'Ontario',
                         unit, 'monthly', 'not adjusted', 'none', ARREARS_DEFINITION)
    SERIES_URLS[series_id] = ARREARS_PAGE

from .trreb_rental import ARCHIVE as RENTAL_ARCHIVE, GEO as RENTAL_GEO, SERIES as RENTAL_SERIES
for series_id, (label, unit, definition) in RENTAL_SERIES.items():
    SERIES[series_id] = (label, 'TRREB rental', 'Rental Market Report, apartments', RENTAL_GEO, unit,
                         'quarterly', 'not adjusted', 'none', definition)
    SERIES_URLS[series_id] = RENTAL_ARCHIVE
