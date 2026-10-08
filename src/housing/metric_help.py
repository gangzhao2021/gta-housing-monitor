"""Qualitative explanations, not model forecasts or investment recommendations."""
from html import escape
from .i18n import english, tr
from .catalog import SERIES

BOC = 'https://www.bankofcanada.ca/2008/06/real-estate-mortgage-markets-monetary-policy/'
RATES = 'https://www.bankofcanada.ca/2020/05/whats-behind-your-mortgage-rate/'
# Each explanation separates an economic channel from its limits.
HELP = {
    'boc_policy_rate': (
        '降息通常降低浮动按揭及短期借款成本，改善购房负担能力，对需求和房价形成支持；加息通常相反。',
        '传导需要时间。固定按揭还受债券收益率影响；若就业和收入转弱，降息也不保证房价上涨。',
        'Rate cuts usually reduce variable mortgage and short-term borrowing costs, supporting affordability, housing demand and prices; increases usually work in reverse.',
        'Transmission takes time. Fixed mortgages also depend on bond yields; weaker jobs and incomes can offset the support from rate cuts.', RATES),
    'goc_5y_yield': (
        '五年国债收益率是固定按揭定价的重要参考。收益率下降，通常有利于降低固定贷款成本、支持购房需求。',
        '银行融资成本、风险溢价和竞争也影响报价，不会一比一传导；市场可能提前反映预期降息。',
        'Five-year government bond yields are an important benchmark for fixed mortgage pricing. Lower yields can reduce financing costs and support homebuying demand.',
        'Funding costs, risk premiums and competition also affect offers. Pass-through is not one-for-one, and anticipated rate cuts may already be priced in.', RATES),
    'mortgage_uninsured_fixed_5plus': (
        '按揭利率上升，在相同本金和摊还期下会增加月供，压缩购房预算，通常给房价带来下行压力。',
        '这里是已发生贷款的加权均值，包含续贷和再融资，不是今天的银行报价；变化也受贷款构成影响。',
        'Higher mortgage rates increase payments for a given principal and amortization, reducing purchasing power and usually putting downward pressure on prices.',
        'This is a weighted average of actual lending, including renewals and refinancing, not a current bank offer. Loan composition also affects changes.', RATES),
    'trreb_sales': ('成交增加可能反映需求增强；如果供应没有同步增加，房价上涨压力可能更大。','需结合挂牌、季节性和房型构成判断；成交回升本身不等于房价上涨。','More sales may signal stronger demand. If supply does not rise alongside it, upward price pressure may increase.','Read alongside listings, seasonality and the mix of homes sold; more sales alone do not imply rising prices.', BOC),
    'trreb_new_listings': ('新增挂牌增加，为买家提供更多选择，通常缓解卖方议价优势。','如果成交增长更快，市场仍可能趋紧；挂牌不是新建住房，也不代表最终一定出售。','More new listings give buyers more choice and may reduce sellers’ bargaining power.','The market can still tighten if sales grow faster. Listings are not newly built homes and may not sell.', BOC),
    'trreb_active_listings': ('有效挂牌是当前可售选择。相对成交量而言，库存越多，买家通常越有议价空间。','库存也可能因销售放缓而积累；需结合成交速度、季节性及地区看待。','Active listings measure available resale choice. More inventory relative to sales generally gives buyers more bargaining room.','Inventory may accumulate because sales slow; consider turnover, seasonality and location.', BOC),
    'moi_raw': ('库存月数 = 月末有效挂牌 ÷ 当月成交。数值上升通常表示消化库存更慢，价格压力偏弱；下降通常相反。','这是原始月度比率，不是实际售罄预测，也没有适用于所有地区和房型的固定分界线。','Months of inventory equals active listings divided by monthly sales. A rise usually indicates slower absorption and softer price pressure; a fall suggests the reverse.','This raw monthly ratio is not a sell-out forecast. There is no universal threshold across areas and property types.', BOC),
    'snlr_raw': ('成交相对新增挂牌越多，买卖双方通常越偏向卖方，房价更容易获得支持。','这是当月流量比率，不包含全部库存；季节性或少量成交也会使比率波动。','More sales relative to new listings typically favour sellers and can support prices.','This monthly flow ratio excludes existing inventory; seasonality and small sales counts can move it sharply.', BOC),
    'toronto_unemployment_rate': ('失业率上升通常削弱收入预期和贷款承受能力，抑制购房需求，对房价形成压力。','也可能推动更多家庭继续租房；降息、人口变化和供应情况会影响最终结果。','Higher unemployment typically weakens income expectations and borrowing capacity, putting pressure on homebuying demand and prices.','More households may remain renters; interest rates, population changes and supply affect the outcome.', BOC),
    'toronto_employment_rate': ('就业率上升意味着更多劳动年龄人口有工作，通常支持收入、购房能力和住房需求。','还要看工资、工时和岗位稳定性；就业增加不一定足以抵消更高的贷款成本。','A higher employment rate means more working-age people have jobs, generally supporting incomes, purchasing power and housing demand.','Wages, hours and job security matter too; employment gains may not offset higher borrowing costs.', BOC),
    'toronto_participation_rate': ('参与率反映工作或正在找工作的人口占比。上升可能扩大劳动力供给，但对购房需求的影响取决于是否找到工作。','参与率上升也可能伴随失业率上升，不能直接解读为房价利好或利空。','Participation measures people working or seeking work. A rise can expand labour supply, but housing demand depends on whether jobseekers find work.','Participation and unemployment can rise together. This is not a direct positive or negative price signal.', BOC),
    'toronto_cma_2011_starts': ('开工增加意味着未来住房供应可能扩大，长期有助于缓解供需紧张。','从开工到交付需要时间，项目可能延迟；开工也可能是在回应此前需求上涨。','More starts can expand future housing supply and ease pressure over time.','Delivery takes time and projects can be delayed; more starts may also be responding to earlier demand growth.', BOC),
    'toronto_cma_2011_completions': ('竣工增加意味着更多住房可以进入使用阶段，通常有助于缓解住房和租赁供给压力。','影响取决于位置、房型、用途及同期新增家庭数量；不代表这些住房全部挂牌出售。','More completions make additional homes available for use and can ease housing and rental supply pressures.','Location, type, tenure and household growth matter. Completed homes are not all listed for sale.', BOC),
    'toronto_cma_2011_under_construction': ('在建住宅反映未来供应管线，较多项目最终交付可能缓解房价和租金压力。','在建增加也可能源于工期变长；不能把在建总量当作短期上市量或 condo 预售库存。','Homes under construction represent a supply pipeline that may ease price and rent pressures when delivered.','A larger pipeline can also reflect longer build times. It is not near-term listed supply or condo presale inventory.', BOC),
    'toronto_cma_2021_population': ('人口增长通常增加居住需求。若新增家庭增长快于可用住房供应，房价和租金可能面临上行压力。','人口不等于家庭数量，也不等于购房者数量；收入、年龄结构和合住情况都会影响需求。','Population growth generally increases housing needs. Prices and rents may face upward pressure if household growth outpaces available supply.','People are not the same as households or buyers; incomes, age and shared housing affect demand.', BOC),
    'wti_cushing_spot_price': ('油价变化可能经运输、部分建材、通胀和利率影响住房成本与需求，也可能影响能源相关收入。','这是美国 WTI 月均价，不是 Ontario 零售能源或 GTA 建筑成本；传导方向与净影响尚未验证，不能据此预测房价。','Oil prices can affect transport, some materials, inflation and rates, as well as energy-sector income.','This U.S. WTI monthly average is not Ontario retail energy or GTA construction cost. Its net housing effect is unverified.', 'https://www.eia.gov/dnav/pet/hist/rwtcm.htm'),
    'usd_cad_monthly': ('汇率变化可能改变进口建材和设备成本，也会影响贸易收入及购买力。','数值是每美元对应的加元；上升代表加元走弱，不直接衡量外国买家需求，也不能单独推断 GTA 房价。','Exchange rates can affect imported materials and equipment costs, trade income and purchasing power.','The value is Canadian dollars per U.S. dollar; a rise means a weaker Canadian dollar. It does not directly measure foreign-buyer demand or predict GTA prices.', 'https://www.bankofcanada.ca/rates/exchange/monthly-exchange-rates/'),
    'boc_energy_price_index': ('能源商品价格可能经通胀、运输及建造投入影响住房市场，也可能影响能源行业收入。','这是加拿大央行能源商品指数，不是 WTI 或本地账单；底层缺源可能沿用前值，历史数据也会修订。','Energy commodity prices can affect housing through inflation, transport and building inputs, and energy-sector income.','This Bank of Canada index is neither WTI nor a local energy bill. Some missing inputs may carry forward, and history may be revised.', 'https://www.bankofcanada.ca/rates/price-indexes/bcpi/'),
    'toronto_residential_construction_cost_index': ('住宅建造报价成本上升可能降低项目可行性，经过开发和交付时滞影响未来供应。','季度指数以首月存储，基期为 2023=100；不含地价和融资成本，也不是转售房价或新房供给数量。','Higher residential construction quotes can affect project viability and, after a lag, future housing supply.','This quarterly index is stored by its first month and uses 2023=100. It excludes land and financing costs and is neither a resale price nor a count of new homes.', 'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810028901'),
    'ontario_net_interprovincial_migration': ('省际净迁移可反映 Ontario 与其他省份之间的人口流动，长期可能影响住房需求。','这是 Ontario 季度人数，可为负值；不能当作 Toronto CMA 人口、家庭或购房人数。历史估计可能修订。','Net interprovincial migration tracks movement between Ontario and other provinces and may affect housing demand over time.','This is a quarterly Ontario person count that can be negative, not Toronto CMA households or homebuyers. History may be revised.', 'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710002001'),
    'ontario_net_international_migration': ('国际净迁移反映跨境流动与非永久居民净变化，可影响省级住房需求背景。','这是 Ontario 季度人数，可为负值；不能当作 Toronto CMA 新增家庭或购买需求。历史估计可能修订。','Net international migration includes cross-border flows and changes in non-permanent residents, informing provincial housing-demand context.','This is a quarterly Ontario person count that can be negative, not Toronto CMA new households or buyers. History may be revised.', 'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710004001'),
}
PRICE = ('HPI 本身就是房价的衡量：上升表示同类住房变贵，下降表示变便宜。它反映已经签约的成交价格，是市场的结果，不是原因。','判断后市要看供需（库存月数、成交／新挂牌比）、利率和收入；不能把过去的涨跌直接外推到未来。','HPI is itself a measure of home prices: a rise means comparable homes cost more. It reflects prices already agreed, so it is an outcome rather than a cause.','To judge what comes next, look at supply and demand (months of inventory, sales-to-new-listings), rates and incomes rather than extrapolating past changes.', BOC)
RENT = ('租金上升可能反映租赁需求强于供应，也可能提高出租物业的潜在收入，对投资需求形成支持。','租金与房价并非同步变化；利率、费用、空置风险以及挂牌样本构成都很重要。','Higher rents may reflect rental demand exceeding supply and can support investment demand through potential rental income.','Rents and home prices need not move together. Interest rates, costs, vacancy risk and the sample mix also matter.', BOC)
VACANCY = ('空置率上升通常意味着租客选择增加，租金上涨压力减弱，也可能削弱出租物业的收入预期。','对房价的影响是间接的；需结合地区、房型、租金和融资成本判断。','Higher vacancy generally gives renters more choice, easing rent pressure and potentially weakening expected rental income.','The effect on home prices is indirect and depends on location, unit type, rents and financing costs.', BOC)


from .background_series import CONFIG as BACKGROUND_CONFIG, url_for
for c in BACKGROUND_CONFIG.values():
    if not c.get('archived'):
        HELP[c['id']] = ('作为背景参考，帮助理解市场环境；本项目尚未验证它对房价的预测作用。', '按来源的地区与所属期解读，不同来源不直接相加或比较。',
                        'Context for understanding the market; this project has not validated it as a predictor of prices.', 'Read it with its own geography and reference period; do not add or compare across sources directly.', url_for(c))


from .teranet import URL as TERANET_URL
for _field in ('teranet_toronto_index', 'teranet_toronto_index_sa'):
    HELP[_field] = ('它本身就是房价的衡量，可与 TRREB 的 MLS HPI 相互印证；历史从 1998 年开始，适合看长期走势。',
                    '重复交易指数会随新配对修订历史，发布晚于 TRREB；地区与方法不同，不与 TRREB HPI 合并或互相替代。',
                    'It is itself a measure of home prices and a cross-check on TRREB MLS HPI, with history back to 1998 for long-run trends.',
                    'Repeat-sales history is revised as new pairs arrive and is released later than TRREB; method and area differ, so it is not merged with TRREB HPI.',
                    TERANET_URL)


# What each measure is, in plain words; shown before how it relates to prices.
DEFINITIONS = {
    'boc_policy_rate': ('加拿大央行设定的隔夜利率目标，即银行之间隔夜借钱的利率。各银行的优惠利率（Prime）和浮动按揭利率随它变动。',
                        "The Bank of Canada's target for the overnight rate at which banks lend to each other. Banks' prime rates and variable mortgage rates move with it."),
    'goc_5y_yield': ('加拿大政府五年期国债在市场上的年收益率，也就是投资者借钱给政府五年要求的回报。',
                     'The market yield on five-year Government of Canada bonds: the annual return investors require to lend to the government for five years.'),
    'mortgage_uninsured_fixed_5plus': ('银行当月实际新发放的、无需按揭保险（首付至少 20%）的五年及以上固定利率按揭的平均利率。',
                                       'The average rate on new uninsured (at least 20% down) fixed-rate mortgages of five years or longer that banks actually lent that month.'),
    'trreb_sales': ('当月在 TRREB 的 MLS 系统上签约成交的二手房套数，覆盖大多伦多及周边地区。',
                    "Resale homes sold (deals agreed) that month through TRREB's MLS system across the Greater Toronto Area and surrounding areas."),
    'trreb_new_listings': ('当月新挂到 MLS 上出售的房源数。', 'Homes newly listed for sale on the MLS that month.'),
    'trreb_active_listings': ('月底仍在 MLS 上挂牌出售的房源总数，也就是买家当时能选的库存。',
                              'Homes still listed for sale on the MLS at month-end: the inventory buyers can choose from.'),
    'moi_raw': ('按当月的成交速度，把月底所有在售房源卖完需要几个月。例如 5 表示约需 5 个月。',
                'How many months it would take to sell all homes listed at month-end at that month’s sales pace. For example, 5 means about five months.'),
    'snlr_raw': ('当月成交套数 ÷ 当月新挂牌套数。例如 50% 表示每两套新挂牌对应一套成交。',
                 'Sales divided by new listings in the month. For example, 50% means one sale for every two new listings.'),
    'toronto_unemployment_rate': ('Toronto 都会区想工作、正在找工作却没有工作的人，占全部劳动力的比例（已剔除季节波动）。',
                                  'People in the Toronto CMA who want work and are looking but have no job, as a share of the labour force (seasonally adjusted).'),
    'toronto_employment_rate': ('Toronto 都会区 15 岁及以上人口中有工作的人所占的比例。', 'The share of people aged 15 and over in the Toronto CMA who have a job.'),
    'toronto_participation_rate': ('Toronto 都会区 15 岁及以上人口中，有工作或正在找工作的人所占的比例。',
                                   'The share of people aged 15 and over in the Toronto CMA who are working or looking for work.'),
    'toronto_cma_2011_starts': ('当月开始动工（打地基）的新住宅套数，Toronto 都会区。', 'New homes on which construction began that month in the Toronto CMA.'),
    'toronto_cma_2011_completions': ('当月完工、可以入住的新住宅套数，Toronto 都会区。', 'New homes finished and ready to occupy that month in the Toronto CMA.'),
    'toronto_cma_2011_under_construction': ('月底已经开工但还没完工的住宅总套数，Toronto 都会区。',
                                            'Homes started but not yet finished at month-end in the Toronto CMA.'),
    'toronto_cma_2021_population': ('统计局估计的 Toronto 都会区每年 7 月 1 日人口。', "Statistics Canada's estimate of the Toronto CMA population on July 1 each year."),
    'wti_cushing_spot_price': ('美国 WTI 原油每桶的月平均现货价格（美元）。', 'The monthly average spot price of U.S. WTI crude oil, in U.S. dollars per barrel.'),
    'usd_cad_monthly': ('1 美元当月平均能兑换多少加元。', 'How many Canadian dollars one U.S. dollar bought on average that month.'),
    'boc_energy_price_index': ('加拿大央行编制的能源类大宗商品价格指数，包括原油、天然气等。',
                               "The Bank of Canada's price index for energy commodities such as crude oil and natural gas."),
    'toronto_residential_construction_cost_index': ('统计局调查的、在 Toronto 建造住宅的承包商报价指数，2023 年 = 100。',
                                                    "Statistics Canada's index of contractors' prices to build homes in Toronto, 2023 = 100."),
    'ontario_net_interprovincial_migration': ('每季从其他省份搬来 Ontario 的人数减去从 Ontario 搬走的人数。',
                                              'People moving to Ontario from other provinces minus those leaving, each quarter.'),
    'ontario_net_international_migration': ('每季从国外移入 Ontario 的人数减去移出的人数，包括留学生、工签等非永久居民的净变化。',
                                            'People arriving in Ontario from abroad minus those leaving each quarter, including the net change in non-permanent residents such as students and workers.'),
    'teranet': ('Teranet 与国家银行编制的房价指数：比较同一套房子前后两次在土地登记处登记的成交价来计算价格变化，2005 年 6 月 = 100。',
                'House price index by Teranet and National Bank: compares the registered prices of the same homes sold twice to measure price change, June 2005 = 100.'),
    'hpi': ('MLS 房价指数：把每月成交的房子按面积、房龄、卧室数等特征折算成一套“标准房”的价格，避免“这个月豪宅卖得多、均价就高”的偏差。基准价是标准房的价格，指数是相对 2005 年 1 月（=100）的倍数。',
            'MLS Home Price Index: prices each month’s sales as a standard home with typical size, age and bedrooms, so a month with more luxury sales does not inflate it. The benchmark is that standard home’s price; the index is relative to January 2005 = 100.'),
    'asking_rent': ('Rentals.ca 网站上出租房源的平均挂牌要价（加元／月），是房东开价，不是最终签约租金。',
                    'The average asking rent of rental listings on Rentals.ca (CAD per month): what landlords ask, not the final signed rent.'),
    'cmhc_rent': ('CMHC 每年 10 月调查的出租单位平均实际月租（加元），包括已住租客，而不只是新出租的。',
                  "CMHC's October survey of average monthly rents actually paid (CAD), including sitting tenants, not only new leases."),
    'lease_rent': ('季度内经 TRREB MLS 租出的 condo 公寓平均签约月租（加元）。', 'The average signed monthly rent (CAD) of condo apartments leased through TRREB’s MLS in the quarter.'),
    'townhouse_lease_rent': ('季度内经 TRREB MLS 租出的镇屋（townhouse）平均签约月租（加元）；不含独立屋、半独立屋。', 'The average signed monthly rent (CAD) of townhouses leased through TRREB’s MLS in the quarter; detached and semi-detached houses are not included.'),
    'vacancy': ('CMHC 每年 10 月调查时，空着待租的出租单位占全部出租单位的比例。', 'The share of rental units that were empty and available for rent at CMHC’s October survey.'),
}


def definition(field):
    """Plain-language description of what the measure is."""
    if field in DEFINITIONS:
        return DEFINITIONS[field]
    if field.startswith('teranet_'):
        return DEFINITIONS['teranet']
    if field in ('trreb_hpi_benchmark', 'trreb_hpi_composite'):
        return DEFINITIONS['hpi']
    if 'vacancy' in field:
        return DEFINITIONS['vacancy']
    if field.startswith('gta_condo_lease_rent_'):
        return DEFINITIONS['lease_rent']
    if field.startswith('gta_townhouse_lease_rent_'):
        return DEFINITIONS['townhouse_lease_rent']
    if field.startswith(('toronto_asking_rent_', 'regional_asking_')):
        return DEFINITIONS['asking_rent']
    if 'rent_' in field:
        return DEFINITIONS['cmhc_rent']
    config = next((c for c in BACKGROUND_CONFIG.values() if c['id'] == field), None)
    if config:
        return (config['definition'], config['title'])
    return None


HELP['gta_condo_lease_listed'] = ('出租挂牌多于租出时，租客选择增加、租金承压，也会削弱投资型买家的回报预期。', '只含经 TRREB MLS 出租的 condo 公寓，不代表全部出租房源。',
                                  'When more units are listed than leased, renters gain choice and rents soften, which can cool investor demand for condos.', 'Covers only condo apartments leased through TRREB’s MLS, not all rentals.', 'https://trreb.ca/market-data/rental-market-report/')
HELP['gta_condo_leased'] = ('租出量反映租赁需求；需求强、租金高时，出租 condo 的回报更好，对 condo 价格有支持。', '季度流量，受季节影响；只含经 TRREB MLS 的 condo 公寓。',
                            'Leases reflect rental demand; strong demand and rents improve condo rental returns and can support condo prices.', 'A seasonal quarterly flow covering only condo apartments leased through TRREB’s MLS.', 'https://trreb.ca/market-data/rental-market-report/')
HELP['gta_townhouse_lease_listed'] = ('出租镇屋挂牌多于租出时，租客选择增加、租金承压。', '只含经 TRREB MLS 出租的镇屋，不含独立屋和半独立屋。',
                                      'When more townhouses are listed than leased, renters gain choice and rents soften.', 'Covers only townhouses leased through TRREB’s MLS; detached and semi-detached houses are excluded.', 'https://trreb.ca/market-data/rental-market-report/')
HELP['gta_townhouse_leased'] = ('租出量反映家庭型租赁需求。', '季度流量，受季节影响；只含经 TRREB MLS 的镇屋。',
                                'Leases reflect demand for family-sized rentals.', 'A seasonal quarterly flow covering only townhouses leased through TRREB’s MLS.', 'https://trreb.ca/market-data/rental-market-report/')
DEFINITIONS['gta_townhouse_lease_listed'] = ('季度内经 TRREB MLS 挂牌出租的镇屋套数。', 'Townhouses listed for lease on TRREB’s MLS during the quarter.')
DEFINITIONS['gta_townhouse_leased'] = ('季度内经 TRREB MLS 实际租出的镇屋套数。', 'Townhouses actually leased through TRREB’s MLS during the quarter.')
DEFINITIONS.update({
    'boc_prime_rate': ('各大银行对最优质客户的基准贷款利率，通常等于央行隔夜利率加 2.2 个百分点；浮动按揭按它加减定价。',
                       "Banks' base lending rate for their best customers, usually the overnight rate plus 2.2 points; variable mortgages are priced off it."),
    'boc_conventional_mortgage_5y': ('银行公布的五年期固定按揭“挂牌利率”。实际放贷通常有折扣，但压力测试常参考它。',
                                     "Banks' posted five-year fixed mortgage rate. Actual loans are usually discounted, but stress tests often refer to it."),
    'toronto_nhpi_total': ('统计局的新房价格指数：开发商对同样规格新建房屋（含土地）的售价变化，不包括二手房。',
                           "Statistics Canada's new housing price index: builders' prices for comparable new homes including land; resale homes are excluded."),
    'ontario_cpi_shelter': ('Ontario 消费物价指数中的“居住”部分，包括房租、按揭利息、物业税、水电等住房开销。',
                            "The shelter part of Ontario's consumer price index: rent, mortgage interest, property tax, utilities and other housing costs."),
    'toronto_permits_units': ('当月获批建筑许可的新增住宅套数，比开工更早反映未来供应。',
                              'New dwelling units authorized by building permits that month; an earlier signal of future supply than starts.'),
    'toronto_starts_condo': ('当月开工的、准备卖给个人的 condo 住宅套数。', 'New homes started that month that are intended to be sold as condos.'),
    'toronto_starts_rental': ('当月开工的、专门建来长期出租的住宅套数（不含个人出租的 condo）。',
                              'New homes started that month that are built to be rented out long-term (not condos rented by individual owners).'),
    'toronto_starts_homeowner': ('当月开工的、卖给自住者或自建的非 condo 住宅套数，主要是独立屋、半独立屋和镇屋。',
                                 'New non-condo homes started that month for owner-occupiers, mostly detached, semi-detached and townhouses.'),
    'toronto_cmhc_absorptions': ('当月完工的新房里已经卖出的套数（含之前预售的），只算自住和 condo 项目。',
                                 'Newly completed homes that were sold (including presales) that month, for owner-occupied and condo projects only.'),
    'toronto_cmhc_unabsorbed_inventory': ('已经完工但还没卖出去的新房套数，只算自住和 condo 项目。',
                                          'Newly completed homes still unsold, for owner-occupied and condo projects only.'),
    'canada_policy_uncertainty': ('根据加拿大主要报纸中同时谈到“经济、政策、不确定”的文章比例编制的指数，越高表示政策不确定性越大。',
                                  'An index built from the share of major Canadian newspaper articles mentioning economy, policy and uncertainty together; higher means more policy uncertainty.'),
})
from .cba_arrears import PAGE as ARREARS_PAGE
DEFINITIONS['ontario_mortgage_arrears_rate'] = ('Ontario 银行发放的住宅按揭中，已经逾期 3 个月以上没还款的笔数占全部按揭的比例。',
                                                'The share of residential mortgages from Ontario banks that are three or more months behind on payments.')
HELP['ontario_mortgage_arrears_rate'] = ('拖欠上升说明部分房主还款吃力，可能增加被迫出售的房源、压制房价；通常在失业上升、续贷利率走高时出现。',
                                         '比例很低（不到 1%），变化慢、滞后于就业；只含银行按揭，不含信用社和私人贷款。',
                                         'Rising arrears show more owners struggling to pay, which can add forced sales and weigh on prices; they tend to follow job losses and higher renewal rates.',
                                         'Rates are very low (under 1%), move slowly and lag employment; only bank mortgages are covered, not credit unions or private lenders.', ARREARS_PAGE)
DEFINITIONS['gta_condo_lease_listed'] = ('季度内经 TRREB MLS 挂牌出租的 condo 公寓套数。', 'Condo apartments listed for lease on TRREB’s MLS during the quarter.')
DEFINITIONS['gta_condo_leased'] = ('季度内经 TRREB MLS 实际租出的 condo 公寓套数。', 'Condo apartments actually leased through TRREB’s MLS during the quarter.')


def explanation(field):
    if field in HELP:
        return HELP[field]
    if field in ('trreb_hpi_benchmark', 'trreb_hpi_composite'):
        return PRICE
    if 'vacancy' in field:
        return VACANCY
    if 'rent_' in field or 'asking_' in field:
        return RENT
    return None


def help_label(field, text):
    content = explanation(field)
    if not content:
        return escape(text)
    zh, caveat_zh, en, caveat_en, url = content
    heading, reference = ('How it relates to home prices', 'Background · Bank of Canada') if english() else ('与房价的关系', '机制参考 · 加拿大央行')
    what = definition(field)
    # The indicator's own name heads the bubble, so the definition reads straight on from it.
    what_html = f'<strong class="bubble-title">{escape(tr(text))}</strong>' + (
        f'<p class="bubble-what">{escape(what[1] if english() else what[0])}</p>' if what else '')
    if field in ('wti_cushing_spot_price', 'usd_cad_monthly', 'boc_energy_price_index',
                 'toronto_residential_construction_cost_index', 'ontario_net_interprovincial_migration',
                 'ontario_net_international_migration') or field in {c['id'] for c in BACKGROUND_CONFIG.values()}:
        reference = ('Official source · ' if english() else '官方来源 · ') + SERIES[field][1]
    body, caveat = (en, caveat_en) if english() else (zh, caveat_zh)
    # Native disclosure supplies touch/keyboard toggling; CSS adds pointer-hover preview.
    return (f'<details class="metric-help"><summary>{escape(tr(text))} <span class="help-icon" aria-hidden="true">ⓘ</span></summary>'
            f'<div class="impact-bubble">{what_html}<span class="bubble-label">{heading}</span><p>{escape(body)}</p>'
            f'<p class="help-caveat">{escape(caveat)}</p>'
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">{reference} ↗</a></div></details>')
