# A股市场图表

这个仓库发布一个自动更新的 GitHub Pages 静态站点。

当前栏目：

- A股融资融券

本地生成：

```powershell
python scripts\build_site.py --all
```

GitHub Actions 会在北京时间交易日 12:30 和 16:00 运行，并把 `site` 目录发布到 GitHub Pages。
