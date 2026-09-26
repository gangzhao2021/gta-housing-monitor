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
}
PRICE = ('HPI 描述标准化住宅价格变化，是市场结果指标。','它本身不是推动房价的原因；应结合需求、供应和融资条件分析，不直接外推未来涨跌。','HPI tracks standardized home prices and is an outcome measure.','It is not itself a driver of prices. Read it alongside demand, supply and financing rather than extrapolating future gains or losses.', BOC)
RENT = ('租金上升可能反映租赁需求强于供应，也可能提高出租物业的潜在收入，对投资需求形成支持。','租金与房价并非同步变化；利率、费用、空置风险以及挂牌样本构成都很重要。','Higher rents may reflect rental demand exceeding supply and can support investment demand through potential rental income.','Rents and home prices need not move together. Interest rates, costs, vacancy risk and the sample mix also matter.', BOC)
VACANCY = ('空置率上升通常意味着租客选择增加，租金上涨压力减弱，也可能削弱出租物业的收入预期。','对房价的影响是间接的；需结合地区、房型、租金和融资成本判断。','Higher vacancy generally gives renters more choice, easing rent pressure and potentially weakening expected rental income.','The effect on home prices is indirect and depends on location, unit type, rents and financing costs.', BOC)


from .background_series import CONFIG as BACKGROUND_CONFIG, url_for
for c in BACKGROUND_CONFIG.values():
    if not c.get('archived'):
        HELP[c['id']] = (c['definition'], '描述性背景，尚未验证预测价值；按来源地区与所属期解释。',
                        c['title'], 'Descriptive context; not a validated forecast. Respect the source geography and reference period.', url_for(c))


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
    heading, reference = ('How it relates to home prices', 'Background · Bank of Canada') if english() else ('如何影响房价', '机制参考 · 加拿大央行')
    if field in ('wti_cushing_spot_price', 'usd_cad_monthly', 'boc_energy_price_index',
                 'toronto_residential_construction_cost_index') or field in {c['id'] for c in BACKGROUND_CONFIG.values()}:
        reference = ('Official source · ' if english() else '官方来源 · ') + SERIES[field][1]
    body, caveat = (en, caveat_en) if english() else (zh, caveat_zh)
    # Native disclosure supplies touch/keyboard toggling; CSS adds pointer-hover preview.
    return (f'<details class="metric-help"><summary>{escape(tr(text))} <span class="help-icon" aria-hidden="true">ⓘ</span></summary>'
            f'<div class="impact-bubble"><strong>{heading}</strong><p>{escape(body)}</p><p>{escape(caveat)}</p>'
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">{reference} ↗</a></div></details>')
