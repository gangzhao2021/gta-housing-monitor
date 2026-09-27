# 市镇着色地图边界证据

2026-09-26 从 Statistics Canada 的 [2021 Census subdivision cartographic boundary layer](https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer/9) 读取 Ontario 八个市镇。REST `query` 使用 `PRUID='35'`、八个 `CSDNAME`、`outSR=4326`、`f=geojson`、`geometryPrecision=5`、`maxAllowableOffset=0.003`；保存原响应为 `municipal_boundaries.geojson`，SHA-256 为 `ccafec64f1a6199c07baee18eae3ddeffa78fdd1e1b37bfc474482a7eeef427e`。数据按 [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada) 署名 Statistics Canada。

仅绘制 CSD 名称及 UID 已核对的 Toronto、Markham、Vaughan、Mississauga、Oakville、Richmond Hill、Aurora、Brampton。Toronto CSD 对应 TRREB `City of Toronto` 全部房型行，其余七项对应同名市镇行。均价环比只在连续两个月均有正数观察值时计算；市镇成交均价受当月房型和地区成交构成影响，不能当作同一套住宅升跌或 HPI。2021 边界经过地图尺度简化，并非物业、街道或当年最新法定边界；North York、Scarborough 和跨市镇租赁组合没有对应 CSD 面，不在此图上填色。
