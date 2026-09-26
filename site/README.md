# Codex Sites 展示版

本目录是看板的只读展示版。Codex Sites 不运行本机 Streamlit／SQLite；网站只提供 `dist/` 中的静态页面与经审核的 `data.json`，不包含管理入口、原始文件、数据库或本机口令。

从项目根目录运行 `python3 site/export_site_data.py`，可从 `data/display_snapshot.json` 重新生成网站数据。先完成本机数据更新、验证和快照审核，再重新发布网站版本。**本机的定时更新目前不会自动同步到 Sites**；页面显示快照生成时间，避免把旧版本当实时数据。

访问权限由 Codex Sites 的站点访问策略控制；每次发布需核对当前访客范围，不能沿用旧的私有部署记录。不要把本机管理口令搬到网站，也不要将 `data/`、SQLite 或 `.env` 复制进 `dist/`。地区地图使用浏览器按需加载的 OpenStreetMap 地理底图，并在地图上持续显示署名；无底图网络时，地区点、勾选框和趋势仍可用。位置点是选区参考，不代表统计边界；原图证据只保存在本机私有数据目录，网站只发布经审核的观察值。底图服务遵守 [OSMF 瓦片使用政策](https://operations.osmfoundation.org/policies/tiles/)：只请求当前视图所需瓦片，不预取或离线打包，保持浏览器 Referer 与缓存策略。发布后应核对线上版本和访问策略，再对外介绍数据时确认统计期及各指标的适用边界。
