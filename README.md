# Linux Desktop Optimizer

一系列独立、可卸载的 Linux 桌面体验优化工具。

## GNOME 面板歌词扩展

[jasmine-panel-lyrics](jasmine-panel-lyrics/README.md)：在 GNOME Shell 50 顶部面板显示歌词，
支持 YesPlayMusic 自动取词、通用本地 LRC、暂停与跳转同步。采用模块化播放器/歌词适配器，
方便添加其他播放器；包含缓存、异步请求取消和失败回退。
安装、歌词命名和验证方法见子目录说明。

## Nautilus IEC 文件大小扩展

为 GNOME 文件管理器的列表视图添加 **大小（IEC） / Size (IEC)** 列，
用 1024 进制显示文件大小，例如 `1.0 KiB`、`1.5 MiB`、`2.0 GiB`。
更大单位由 GLib 自动处理；小于 1024 字节时显示字节数。
文件夹显示 Nautilus 原生项目数；点击 IEC 列标题时复用内置大小排序器。

这是一项新增列扩展。Nautilus 的公开扩展接口没有全局替换内置大小格式的能力，
所以原“大小”列、属性窗口和状态栏仍使用 Nautilus 自己的格式。
可以隐藏原列并启用 IEC 列。

### 安装和使用

当前针对 Nautilus 50（扩展 API 4.1）验证，要求 Python 3、PyGObject、
GTK 4 和 nautilus-python。本项目开发环境为 Ubuntu 26.04 / Nautilus 50.2.2 /
GTK 4.22 / nautilus-python 4.1；其他 Nautilus 版本需要重新验证 UI 排序接入。

Ubuntu / Debian 依赖：

```bash
sudo apt install python3-nautilus python3-gi gir1.2-nautilus-4.1
```

在项目根目录运行，无需 sudo：

```bash
/usr/bin/python3 nautilus-iec-size/install.py install
```

1. 等待正在进行的复制、移动等操作完成，再运行 `nautilus -q`，重新打开“文件”。
2. 切换至列表视图，在列设置（通常是右键列标题或视图菜单的“可见列”）中启用
   **大小（IEC） / Size (IEC)**，按需隐藏原“大小”列。
3. 如果希望应用于其他文件夹，在 Nautilus 提供的列设置中选择应用为默认值；
   已有单独视图设置的文件夹可能仍需手动调整。

安装器遵循 `XDG_DATA_HOME`，默认安装到
`~/.local/share/nautilus-python/extensions/ldo_iec_size.py`。
重复安装会更新本扩展；不会修改 Nautilus 的列偏好或其他扩展，也不会自动退出文件管理器。
安装器检查 GI 接口；仍需确保发行版的 `python3-nautilus` 加载器已安装。

### 行为与限制

- 使用 GLib 的 IEC 格式化，数字、小数点和字节名称遵循桌面语言设置。
- 使用 GIO 异步读取元数据，支持其可访问的本地和远程文件，不读取文件内容。
- 显示文件的逻辑大小；稀疏文件不是磁盘实际占用量。
- 文件夹（包括指向文件夹的链接）复用内置“大小”属性，显示 `0 items`、`12 个项目`
  等本地化文本。隐藏文件的计数规则、远程位置策略、计数禁用策略均遵循 Nautilus。
  不另行扫描或递归统计；原生计数尚未可用时显示 `—`。
- 原生目录计数发生变化时同步更新。Nautilus 不会实时监控所有子文件夹内容，
  修改子文件夹后可能需要 F5 刷新，与内置列一致。
- 文件符号链接跟随目标；特殊文件、断链、不可访问文件或无大小元数据时显示 `—`。
- 取消加载目录时取消未完成请求；后续刷新会重新查询大小。
- IEC 列直接共享同一视图中内置“大小”列的 GTK 排序器：文件按字节数、
  目录按原生项目数排序，升降序、同大小文件处理和“文件夹优先”设置均与内置列一致。
  隐藏原“大小”列不影响排序。通过 GTK 的视图显示事件接入，不定时遍历窗口。
- 排序接入依赖 Nautilus 的 GTK 列 ID（`size` 和 `Ldo::IecSize`），属于有版本依赖的
  UI 集成，并非 Nautilus 扩展 API 提供的排序接口。若在匹配的视图中找不到原生排序器，
  会禁用 IEC 列排序并记录警告，避免退回错误的文本排序。
- GLib 保留一位小数，接近单位边界时可能显示 `1024.0 KiB`；这属于显示舍入。
- 已通过隔离的真实 Nautilus 50.2.2 会话验证：隐藏原大小列后复用原生排序器、
  两种“文件夹优先”设置下的升降序、同大小文件、目录符号链接和 F5 后项目数更新。
  使用 GTK Broadway 后端自动验证，未覆盖其他版本和所有远程文件系统。

### 卸载

```bash
/usr/bin/python3 nautilus-iec-size/install.py uninstall
```

等待文件操作完成后重启 Nautilus，重新启用原“大小”列即可。

### 开发验证

```bash
/usr/bin/python3 -m unittest discover -s nautilus-iec-size/tests -v
```

无需第三方测试框架，但需要上面的系统 GI 依赖。
安装器支持 `--data-home /绝对路径`，可用于临时目录安装测试。

真实 GTK 排序测试（需要可用的 GTK 显示会话；普通测试运行会跳过这 4 项）：

```bash
LDO_TEST_GTK=1 /usr/bin/python3 -m unittest discover -s nautilus-iec-size/tests -v
```

真实 Nautilus 集成测试（需要 `gtk4-broadwayd`、`dbus-run-session` 和 Nautilus）：

```bash
/usr/bin/python3 nautilus-iec-size/tests/run_nautilus_smoke.py
```

该测试自动创建临时配置、内存设置、私有 D-Bus 会话和仅监听本机的 Broadway 显示服务，
不安装到用户扩展目录，也不退出用户正在使用的 Nautilus。测试结束自动清理临时文件。

接口依据：[ColumnProvider](https://gnome.pages.gitlab.gnome.org/nautilus-python/class-nautilus-python-column-provider.html)、
[异步 InfoProvider](https://gnome.pages.gitlab.gnome.org/nautilus-python/class-nautilus-python-info-provider.html)、
[扩展加载路径](https://gnome.pages.gitlab.gnome.org/nautilus-python/nautilus-python-overview.html)。
排序实现参考 Nautilus 50.2 的
[列表视图](https://github.com/GNOME/nautilus/blob/50.2/src/nautilus-list-view.c)和
[文件模型](https://github.com/GNOME/nautilus/blob/50.2/src/nautilus-file.c)。
