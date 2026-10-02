# Panel Lyrics（第一版）

在 GNOME 顶部面板显示本地 LRC 当前歌词。针对 GNOME Shell 50 开发，
无需 Node.js、Python 后台进程或在线服务。

## 安装

在仓库根目录执行：

```bash
bash panel-lyrics/package.sh
gnome-extensions install --force /tmp/panel-lyrics-dist/panel-lyrics@linux-desktop-optimizer.shell-extension.zip
```

首次安装后，保存工作，注销并重新登录，再执行：

```bash
gnome-extensions enable panel-lyrics@linux-desktop-optimizer
```

也可以在 GNOME“扩展”应用中启用 **Panel Lyrics**。更新已加载的扩展后也需
重新登录，让 GNOME Shell 加载新代码；仅停用再启用不会刷新 JavaScript 模块。

## 使用

打开支持 MPRIS 的播放器并播放歌曲。第一版按 D-Bus 名称排序，选择找到的
第一个播放器，并持续使用它直到退出；使用时建议只打开一个播放器。
播放器必须提供播放进度，才能同步歌词。

歌词按以下顺序查找（文件名区分大小写）：

1. 本地音频同目录、同名 `.lrc`，例如 `/home/me/Music/song.flac` 对应
   `/home/me/Music/song.lrc`。播放器需要提供 `file://` 音频地址。
2. 系统音乐目录的 `Lyrics/歌手 - 歌名.lrc`。
3. 系统音乐目录的 `Lyrics/歌名.lrc`。

音乐目录遵循 XDG 设置；未配置时使用 `~/Music`。多个歌手以 `, ` 连接。
文件名中的 `/`、`\` 和控制字符用 `_` 替换。

使用 UTF-8 编码的带时间戳 LRC，例如：

```lrc
[ti:示例歌曲]
[ar:示例歌手]
[00:01.00]第一句歌词
[00:05.50]第二句歌词
[00:10.000][00:20.000]重复的歌词
```

支持多时间戳、毫秒精度及 `[offset:毫秒]`；正 offset 提前显示，负值延后。
暂停时保留当前句，拖动播放进度后更新。无歌词、空白间奏或首句尚未开始时显示歌名；
停止播放显示“已停止”，播放器退出显示“等待播放器”。

点击面板歌词可查看当前歌曲、播放器和实际歌词路径。添加或修改 LRC 后，
点击菜单里的 **重新加载歌词**。过长的歌词以省略号显示，最大宽度 420px。

## 限制

- 第一版不含在线搜索、逐字高亮、播放器选择器或设置页面。
- 大约每 300ms 异步读取播放器信息，最多一个请求在途，不阻塞 Shell 等待 D-Bus。
- 未找到歌词时不会反复扫描磁盘；切歌或手动重新加载才会读取文件。
- 不提供进度的播放器只能显示歌名。播放器元数据、进度实现的差异仍需实际适配。
- 尚未覆盖其他 GNOME 大版本，metadata 仅声明支持 50。

## 验证

```bash
gjs -m panel-lyrics/tests/test-lyrics.js
GIO_USE_VFS=local dbus-run-session -- gjs -m panel-lyrics/tests/test-player.js
bash panel-lyrics/tests/smoke-shell.sh
bash panel-lyrics/package.sh
```

测试覆盖 LRC 解析和边界、真实私有 D-Bus 服务的播放状态/跳转/换曲/断开重连，
以及隔离的 GNOME Shell 50 中实际面板文字、本地歌词读取、暂停、双向跳转、
重新加载、无歌词回退和扩展启停。Shell 测试使用临时目录、私有 D-Bus 和虚拟屏幕，
不会重启用户桌面，也不会安装测试扩展到用户目录；需要系统支持 headless GNOME Shell。
未对真实音乐播放器进行手动试听验证。

## 卸载

```bash
gnome-extensions disable panel-lyrics@linux-desktop-optimizer
gnome-extensions uninstall panel-lyrics@linux-desktop-optimizer
```

不会删除你的 LRC 文件。

参考：[GNOME 扩展开发](https://gjs.guide/extensions/development/creating.html)、
[MPRIS Player 接口](https://specifications.freedesktop.org/mpris/latest/Player_Interface.html)。
