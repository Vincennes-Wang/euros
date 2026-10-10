# PROGRESS
- 状态：进行中
- 当前阶段：4 每月自动更新（代码完成，待线上首次运行）
- 累计用时：3 小时
- 线上地址：https://vincennes-wang.github.io/euros/

## 最近一次工作（2026-10-10）
- 完成：
  - `scraper/scrape.py --strict`：出现任何 WARNING、年份退回 `data/raw` 存档、币被 dropped、图片下载失败时，退出码为 1。默认行为不变。
  - `.github/workflows/monthly-scrape.yml`：每月 1 日 06:17 UTC 运行，也可手动触发。抓取 → 缩略图 → validate → pytest → JS 测试，全部通过才提交 `data/`（含 `data/last_checked.txt`）。有新 id 时自动建 Issue“新纪念币待翻译：N 枚”。
  - `CLAUDE.md` 补充每月更新和 strict 规则。
- 验证结果：
  - pytest 36 项通过（新增 4 项：存档回退、币消失、图片失败、离线正常）。故意关掉 strict 判断（3 项失败）、去掉存档回退警告（1 项失败），已改回。
  - 在临时 worktree 中逐条运行 workflow 命令（未装 act）：在线 strict 抓取 23 个年份无 WARNING，退出码 0；缩略图、validate（OK）、pytest、node 13 项均通过；提交作者为 github-actions[bot]。
  - 模拟 4 枚新币，Issue 标题和正文正确；无新币时不建 Issue。YAML 解析正确。
  - ECB 2026 页面目前 404，按“未发布”跳过。

## 下次从这里继续
1. 确认首次线上运行结果（手动触发一次），并确认 bot 推送后 Pages 是否自动重新部署。
2. 新币出现后：补 `description_zh` 翻译，关闭对应 Issue。
3. 拍照识别：先用实拍照片验证可行性。

## 未解决问题
- ECB 2022 联合发行页面缺德国版本图片。
- 手机窄屏布局未用真机检查（headless Chrome 最小窗口宽度约 500 px，截不到 390 px）。
- 工作流失败时不提交 `last_checked.txt`；连续约 2 个月失败，GitHub 会停用定时任务（失败会发邮件提醒）。
