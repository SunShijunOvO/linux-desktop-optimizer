# GNOME 应用菜单编辑器

使用 **GTK 4 + libadwaita** 的原生桌面应用，提供类似 Alacarte 的启动项编辑功能。
本机验证环境：GTK 4.22、libadwaita 1.9、Python 3.14；要求 libadwaita ≥ 1.5、GTK ≥ 4.12。

## 启动与安装

Ubuntu / Debian 依赖：

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

在仓库根目录直接运行：

```bash
/usr/bin/python3 gnome-menu-editor/menu_editor.py
```

安装到当前用户的应用菜单（无需 sudo）：

```bash
/usr/bin/python3 gnome-menu-editor/install.py install
```

随后在 GNOME 概览搜索“应用菜单编辑器”。安装器复制程序到
`$XDG_DATA_HOME/linux-desktop-optimizer/menu-editor`，默认位于 `~/.local/share`。
代码更新后重新安装即可。卸载命令：

```bash
/usr/bin/python3 gnome-menu-editor/install.py uninstall
```

卸载只移除编辑器，保留编辑过的启动项。可通过 `--data-home /绝对路径` 隔离安装测试。

## 使用

- 左侧搜索名称、命令或 desktop ID，按常见应用分类筛选；包括已隐藏的启动项。
- 编辑名称、说明、图标名称或路径、启动命令、工作目录、终端模式与分类。
- `Ctrl+N` 新建，`Ctrl+S` 保存，`Ctrl+F` 搜索。切换应用、刷新或关闭时会提示保存未完成修改。
- 关闭“显示在应用菜单中”隐藏启动项。开启并保存时清除 `Hidden`、`OnlyShowIn`、`NotShowIn` 显示限制。
- “删除用户覆盖 / 自定义启动项”恢复同名系统项；没有系统项时删除自定义启动项。不会卸载应用。
- 系统文件不被改写，修改保存在用户 `applications` 目录，以相同 desktop ID 覆盖。
  按 XDG 优先级读取，兼容子目录 ID，以及已纳入 `XDG_DATA_DIRS` 的 Flatpak / Snap 导出目录。
- 保留未编辑的其他键、其他语言翻译、注释和桌面快捷动作。名称和说明会同步更新当前语言的已有翻译。

### 一键添加 `--no-sandbox`

选择应用，在“启动设置”点击“一键添加”，然后保存。按钮不重复添加参数，保留命令的引号，
将参数放到 `%U` / `%F` 等文件占位符、`--` 和 Flatpak 文件转发标记之前。
例如 `example %U` → `example --no-sandbox %U`。常规 `flatpak run … 应用ID @@u %U @@` 也受支持。
保存时会关闭该启动项的 D-Bus 激活，确保 GNOME 使用 `Exec` 命令；手工改变命令时也会关闭 D-Bus 激活。

该选项关闭 Chromium / Electron 等应用自身的沙箱，程序需支持此参数。仅对确实需要的应用使用。
只修改主启动命令；右键快捷动作保持原样。对于 `sh -c` 等 shell 脚本拒绝自动添加，需手工编辑；
自定义包装器可能有自己的参数规则，应检查生成的命令。编辑器不会运行待编辑的命令。

## 范围

编辑标准 `.desktop` 启动项和分类，不编辑旧式 `.menu` XML，不管理 GNOME 应用文件夹或网格排序。
GNOME 通常会自动刷新启动项；已经运行的应用需要关闭后重启才能使用新参数。
菜单是否显示还受 `TryExec`、应用安装状态和 GNOME 自身规则影响。

## 验证

```bash
/usr/bin/python3 -m unittest discover -s gnome-menu-editor/tests -v
/usr/bin/python3 gnome-menu-editor/tests/run_gtk_smoke.py
```

第二项需要 `gtk4-broadwayd` 和 `dbus-run-session`，创建仅监听回环地址的临时显示服务，
在隔离数据目录验证新建、编辑、添加参数、保存、隐藏、搜索与删除，不修改用户启动项。

依据：[GTK 4](https://docs.gtk.org/gtk4/)、[libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/)、
[Desktop Entry 规范](https://specifications.freedesktop.org/desktop-entry/latest-single/)。
