# jasmine-panel-lyrics

GNOME Shell 50 顶部面板歌词扩展。支持 **YesPlayMusic 自动获取歌词**，
以及其他 MPRIS 播放器的本地 LRC。扩展使用 GJS、GIO 和 libsoup 3，
无需额外常驻进程。

## 安装和旧版迁移

在仓库根目录执行，无需 sudo：

```bash
bash jasmine-panel-lyrics/install.sh
```

安装器先打包和安装新扩展，再停用并卸载旧的 `panel-lyrics@linux-desktop-optimizer`。
若旧扩展尚未被当前 Shell 识别，安装器会核对 UUID 并将其目录移到
`~/.local/state/jasmine-panel-lyrics/legacy.*` 备份（遵循 `XDG_STATE_HOME`）。
不会删除用户歌词。安装/迁移脚本需要 Python 3。新 UUID 是 `jasmine-panel-lyrics@linux-desktop-optimizer`，
在 GNOME“扩展”应用中显示为 **jasmine-panel-lyrics**。

首次安装或更新已经加载的代码后，通常需要保存工作、注销并重新登录，再执行：

```bash
gnome-extensions enable jasmine-panel-lyrics@linux-desktop-optimizer
```

安装器不会自动注销。仅停用再启用不能保证刷新 GNOME 已缓存的 JavaScript 模块。
只打包、不安装可运行 `bash jasmine-panel-lyrics/package.sh`，
输出到 `/tmp/jasmine-panel-lyrics-dist/`，也可传入输出目录。

## YesPlayMusic

打开桌面版 YesPlayMusic 播放歌曲即可，不需要手动准备 LRC。

- 通过 MPRIS 读取歌名、歌手、播放状态和进度。
- 从 `xesam:url` 的 `/trackid/歌曲ID` 取网易云 ID。**MPRIS 的 `trackid`
  在 YesPlayMusic 中是播放列表序号，不能作为网易云歌曲 ID。**
- 旧版没有上述 URL 时，请求 `http://127.0.0.1:27232/player`；确认歌名、歌手
  与当前 MPRIS 数据匹配后，使用 `currentTrack.id`，避免切歌时串词。
- 歌词来自 `http://127.0.0.1:10754/lyric?id=歌曲ID` 的 `lrc.lyric`。
  扩展只请求本机服务，网易云访问由 YesPlayMusic 内置 API 完成，需要相应网络可用。
- 歌词只在切歌时获取，最多缓存 32 首（仅内存）。点击面板菜单里的
  **重新加载歌词** 会跳过该歌曲缓存；停用扩展清空缓存。
- 请求异步执行，超时 5 秒、响应上限 2 MiB。失败后尝试本地 LRC；若仍无歌词，
  自动在 5、10、20 秒后各重试一次，之后可手动重试。不会持续高频请求歌词接口。
- 不存在歌词、纯音乐、接口不可用时显示歌曲信息；展开菜单可查看歌词来源或错误。

暂停保留当前句，向前/向后拖动进度会重新匹配。读取进度约每 300ms 一次，
但同步精度取决于播放器；YesPlayMusic 上游约每秒更新一次 MPRIS 进度。
当前支持逐行 LRC，不含逐字高亮、翻译/罗马音选择或在线模糊搜索。

## 其他播放器与本地歌词

初次发现播放器时优先选择有专用适配器的播放器（当前为 YesPlayMusic），
同优先级按 D-Bus 名称排序。选定后一直使用它直到连接失效；目前没有手动选择器，
不会因为另一个播放器开始播放就自动切换。建议只打开一个需要显示歌词的播放器。

没有专用歌词适配器的 MPRIS 播放器使用本地 LRC；YesPlayMusic 没有在线歌词或
接口出错时也会尝试本地文件，顺序如下：

1. 本地音频同目录、同名 `.lrc`（播放器需提供 `file://` 音频地址）。
2. 系统音乐目录的 `Lyrics/歌手 - 歌名.lrc`。
3. 系统音乐目录的 `Lyrics/歌名.lrc`。

音乐目录遵循 XDG 设置，未配置时为 `~/Music`。文件名区分大小写，多个歌手用
`, ` 连接，`/`、`\` 和控制字符替换为 `_`。LRC 使用 UTF-8：

```lrc
[00:01.00]第一句歌词
[00:05.50]第二句歌词
[00:10.000][00:20.000]重复歌词
```

支持多时间戳和 `[offset:毫秒]`，正值提前、负值延后。新增/修改文件后点击
**重新加载歌词**。无歌词、空白间奏和首句开始前显示歌名；长歌词省略显示，最大宽度 420px。

## 模块结构和新增播放器

```text
jasmine-panel-lyrics@linux-desktop-optimizer/
├── extension.js             # 依赖组装、启停
├── players/mpris.js         # 播放器发现和统一状态读取
├── providers/index.js       # 歌词适配器注册，按顺序尝试
├── providers/yesplaymusic.js # YesPlayMusic 歌曲 ID、取词和缓存
├── providers/local.js       # 通用本地 LRC 回退
├── transport/http.js        # HTTP、超时、响应大小限制
├── core/controller.js       # 同步、取消、过期结果隔离和重试
├── core/lyrics.js           # LRC 解析和时间戳查找
└── ui/panel.js              # 面板和菜单展示
```

新增支持 MPRIS 的播放器，通常只需要在 `providers/` 添加一个适配器并在
`providers/index.js` 注册到 `LocalLyricsProvider` 前面，无需修改面板或同步逻辑：

```javascript
export class ExampleProvider {
    constructor(http) { this.id = 'example'; this._http = http; }
    supports(state) {
        // 也会只传入 {player} 做发现优先级判断，不能依赖其他字段。
        return state.player === 'org.mpris.MediaPlayer2.example';
    }
    async load(state, cancellable, {refresh = false} = {}) {
        // 异步取词；将 cancellable 传给请求；refresh 时绕过自己的缓存。
        // 使用 parseLrc() 将歌词转换为 entries。
        return {entries: [], source: 'Example 暂无歌词'};
    }
    destroy() { /* 如有自有资源，在此清理 */ }
}
```

统一 `state` 字段：`player`（D-Bus 名称）、`id`、`title`、`artist`、`url`、
`status`（Playing/Paused/Stopped）、`position`（毫秒，缺失时为 null）。
`entries` 为按时间排序的 `{time: 毫秒, text: 字符串}` 数组。
无歌词返回空数组；临时故障抛出异常以触发回退/重试；不直接操作 UI 或设置定时器。
控制器负责切歌/停用时取消请求，即便服务迟到返回，也不会覆盖新歌曲。

非 MPRIS 播放器可以在 `players/` 实现同样的 `read()` / `destroy()` 接口，
再于 `extension.js` 接入；目前只组装了 MPRIS 状态来源。

## 验证

```bash
gjs -m jasmine-panel-lyrics/tests/test-lyrics.js
gjs -m jasmine-panel-lyrics/tests/test-controller.js
GIO_USE_VFS=local dbus-run-session -- gjs -m jasmine-panel-lyrics/tests/test-player.js
gjs -m jasmine-panel-lyrics/tests/test-providers.js
bash jasmine-panel-lyrics/tests/smoke-shell.sh
bash jasmine-panel-lyrics/tests/smoke-shell.sh --yesplay
bash jasmine-panel-lyrics/package.sh
```

覆盖 LRC、D-Bus 播放状态/换曲/重连、真实 HTTP 请求、旧版 ID 兼容、缓存刷新、
格式错误、超时、取消、重试、本地回退及过期响应隔离。Shell 测试在临时目录和私有
D-Bus 中运行 GNOME Shell 50 虚拟屏幕，验证实际面板文字、暂停、双向跳转、
重新加载和扩展启停；YesPlayMusic 模式仅在临时副本替换为测试 HTTP 端口。
不会重启用户桌面或安装测试扩展到用户目录，需要 headless GNOME Shell 和 Python 3。

可选的真实播放器只读验证（需 YesPlayMusic 正在运行并播放有歌词的歌曲）：

```bash
gjs -m jasmine-panel-lyrics/tests/check-live.js
```

已在本机真实 YesPlayMusic 验证歌曲 ID、歌词响应与播放进度读取。
其他 GNOME 大版本、其他播放器发行分支尚未验证，metadata 只声明 GNOME 50。

## 卸载

```bash
gnome-extensions disable jasmine-panel-lyrics@linux-desktop-optimizer
gnome-extensions uninstall jasmine-panel-lyrics@linux-desktop-optimizer
```

参考：[MPRIS](https://specifications.freedesktop.org/mpris/latest/Player_Interface.html)、
[YesPlayMusic MPRIS 源码](https://github.com/qier222/YesPlayMusic/blob/master/src/electron/mpris.js)、
[歌曲 ID 和进度](https://github.com/qier222/YesPlayMusic/blob/master/src/utils/Player.js)、
[播放器 HTTP 接口](https://github.com/qier222/YesPlayMusic/blob/master/src/background.js)、
[歌词 API](https://github.com/qier222/YesPlayMusic/blob/master/src/api/track.js)。
