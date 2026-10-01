# Linux Desktop Optimizer

一系列独立、可卸载的 Linux 桌面体验优化工具。

## Nautilus IEC 文件大小扩展

为 GNOME 文件管理器的列表视图添加 **大小（IEC） / Size (IEC)** 列，
用 1024 进制显示文件大小，例如 `1.0 KiB`、`1.5 MiB`、`2.0 GiB`。
更大单位由 GLib 自动处理；小于 1024 字节时显示字节数。

这是一项新增列扩展。Nautilus 的公开扩展接口没有全局替换内置大小格式的能力，
所以原“大小”列、属性窗口和状态栏仍使用 Nautilus 自己的格式。
可以隐藏原列并启用 IEC 列。

### 安装和使用

要求 Nautilus 43+（扩展 API 4.1）、Python 3、PyGObject、nautilus-python。
本项目开发环境为 Ubuntu 26.04 / Nautilus 50 / nautilus-python 4.1。

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
- 符号链接跟随目标；目录、特殊文件、断链、不可访问文件或无大小元数据时显示 `—`。
  不递归统计文件夹。
- 取消加载目录时取消未完成请求；后续刷新会重新查询大小。
- 扩展列只有字符串属性，因此按本列排序不保证按字节数排序。
  需要精确大小排序时使用 Nautilus 原生“大小”排序。
- GLib 保留一位小数，接近单位边界时可能显示 `1024.0 KiB`；这属于显示舍入。
- 尚未完成真实 Nautilus 窗口中的人工验收；测试覆盖真实 GIO 查询和扩展对象，
  不等价于完整桌面集成验证。

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

接口依据：[ColumnProvider](https://gnome.pages.gitlab.gnome.org/nautilus-python/class-nautilus-python-column-provider.html)、
[异步 InfoProvider](https://gnome.pages.gitlab.gnome.org/nautilus-python/class-nautilus-python-info-provider.html)、
[扩展加载路径](https://gnome.pages.gitlab.gnome.org/nautilus-python/nautilus-python-overview.html)。
