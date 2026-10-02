#!/usr/bin/python3
"""GNOME application menu editor, GTK 4 and libadwaita."""
import sys

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib, Gtk
from desktop_entries import Store, add_no_sandbox, boolean, get

APP_ID = 'io.github.linux_desktop_optimizer.MenuEditor'
CATEGORIES = [('全部应用', ''), ('办公', 'Office'), ('网络', 'Network'), ('影音', 'AudioVideo'),
              ('图形', 'Graphics'), ('开发', 'Development'), ('游戏', 'Game'),
              ('系统', 'System'), ('工具', 'Utility'), ('教育', 'Education')]


class Window(Adw.ApplicationWindow):
    def __init__(self, application, store=None):
        super().__init__(application=application, title='应用菜单编辑器', default_width=1080, default_height=760)
        self.store = store or Store()
        self.current = None
        self.dirty = False
        self.loading = False
        self.fields = {}
        self.connect('close-request', self.close_requested)
        self.overlay = Adw.ToastOverlay()
        self.set_content(self.overlay)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.overlay.set_child(layout)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title='应用菜单编辑器', subtitle='定制你的 GNOME 应用菜单'))
        new = Gtk.Button(icon_name='list-add-symbolic', tooltip_text='新建应用（Ctrl+N）')
        new.connect('clicked', lambda *_: self.guard(self.new_entry))
        header.pack_start(new)
        refresh = Gtk.Button(icon_name='view-refresh-symbolic', tooltip_text='重新加载')
        refresh.connect('clicked', lambda *_: self.guard(self.reload))
        header.pack_start(refresh)
        self.save_button = Gtk.Button(label='保存', sensitive=False)
        self.save_button.add_css_class('suggested-action')
        self.save_button.connect('clicked', lambda *_: self.save())
        header.pack_end(self.save_button)
        layout.append(header)
        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, position=310, vexpand=True)
        split.set_shrink_start_child(False)
        split.set_shrink_end_child(False)
        layout.append(split)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, width_request=260)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(sidebar, f'set_margin_{side}')(12)
        search = Gtk.SearchEntry(placeholder_text='搜索名称或启动命令')
        search.connect('search-changed', lambda *_: self.filter_rows())
        self.search = search
        sidebar.append(search)
        self.category = Gtk.DropDown.new_from_strings([title for title, _ in CATEGORIES])
        self.category.connect('notify::selected', lambda *_: self.filter_rows())
        sidebar.append(self.category)
        self.count = Gtk.Label(xalign=0)
        self.count.add_css_class('dim-label')
        sidebar.append(self.count)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class('navigation-sidebar')
        self.listbox.connect('row-selected', self.selected)
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(self.listbox)
        sidebar.append(scroll)
        split.set_start_child(sidebar)
        self.stack = Gtk.Stack()
        empty = Adw.StatusPage(title='选择一个应用', description='编辑名称、图标与启动命令，或点击左上角 + 新建应用。', icon_name='applications-system-symbolic')
        self.stack.add_named(empty, 'empty')
        editor_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp = Adw.Clamp(maximum_size=760, tightening_threshold=550)
        editor_scroll.set_child(clamp)
        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(form, f'set_margin_{side}')(24)
        clamp.set_child(form)
        self.heading = Gtk.Label(xalign=0, wrap=True)
        self.heading.add_css_class('title-1')
        form.append(self.heading)
        basic = Adw.PreferencesGroup(title='应用信息')
        form.append(basic)
        for key, title in [('Name', '名称'), ('Comment', '说明'), ('Icon', '图标名称或绝对路径')]:
            self.add_field(basic, key, title)
        launch = Adw.PreferencesGroup(title='启动设置', description='启动命令遵循 .desktop 格式；%U / %F 等占位符会原样保留。')
        form.append(launch)
        self.add_field(launch, 'Exec', '启动命令')
        self.add_field(launch, 'Path', '工作目录（可留空）')
        self.terminal = Adw.SwitchRow(title='在终端中运行')
        self.terminal.connect('notify::active', self.changed)
        launch.add(self.terminal)
        sandbox = Adw.ActionRow(title='添加 --no-sandbox', subtitle='关闭应用自身的沙箱隔离，仅对需要此选项的应用使用。')
        sandbox.set_subtitle_lines(2)
        button = Gtk.Button(label='一键添加', valign=Gtk.Align.CENTER)
        button.connect('clicked', self.no_sandbox)
        sandbox.add_suffix(button)
        launch.add(sandbox)
        menu = Adw.PreferencesGroup(title='菜单设置')
        form.append(menu)
        self.add_field(menu, 'Categories', '分类（用分号分隔，例如 Utility;）')
        self.visible = Adw.SwitchRow(title='显示在应用菜单中', subtitle='开启并保存时会清除桌面环境显示限制。')
        self.visible.connect('notify::active', self.changed)
        menu.add(self.visible)
        self.source = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.source.add_css_class('dim-label')
        form.append(self.source)
        self.remove_button = Gtk.Button(label='删除用户覆盖 / 自定义启动项', halign=Gtk.Align.START)
        self.remove_button.add_css_class('destructive-action')
        self.remove_button.connect('clicked', self.remove)
        form.append(self.remove_button)
        self.stack.add_named(editor_scroll, 'editor')
        split.set_end_child(self.stack)
        for name, callback, accel in [('save', self.save, '<Control>s'), ('new', lambda: self.guard(self.new_entry), '<Control>n'), ('search', search.grab_focus, '<Control>f')]:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', lambda _action, _param, cb=callback: cb())
            self.add_action(action)
            application.set_accels_for_action('win.' + name, [accel])
        self.reload()

    def add_field(self, group, key, title):
        field = Adw.EntryRow(title=title)
        field.connect('changed', self.changed)
        group.add(field)
        self.fields[key] = field

    def changed(self, *_):
        if not self.loading:
            self.dirty = True
            self.save_button.set_sensitive(True)

    def toast(self, message):
        self.overlay.add_toast(Adw.Toast(title=message))

    def guard(self, callback):
        if not self.dirty:
            callback()
            return
        dialog = Adw.AlertDialog(heading='保存当前修改？', body='当前应用有尚未保存的修改。')
        dialog.add_response('cancel', '取消')
        dialog.add_response('discard', '放弃修改')
        dialog.add_response('save', '保存')
        dialog.set_response_appearance('save', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('save')
        dialog.set_close_response('cancel')
        def responded(_dialog, response):
            if response == 'discard':
                self.dirty = False
                callback()
            elif response == 'save' and self.save():
                callback()
        dialog.connect('response', responded)
        dialog.present(self)

    def close_requested(self, *_):
        if self.dirty:
            self.guard(self.close)
            return True
        return False

    def reload(self, selected_id=None):
        self.loading = True
        self.current = None
        self.listbox.remove_all()
        self.rows = []
        for entry in self.store.entries():
            row = Gtk.ListBoxRow()
            row.entry = entry
            box = Gtk.Box(spacing=12, margin_top=10, margin_bottom=10, margin_start=8, margin_end=8)
            icon = get(entry.keyfile, 'Icon', 'application-x-executable')
            try:
                image = Gtk.Image.new_from_gicon(Gio.Icon.new_for_string(icon))
            except GLib.Error:
                image = Gtk.Image.new_from_icon_name('application-x-executable')
            image.set_pixel_size(32)
            box.append(image)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
            name = Gtk.Label(label=entry.name, xalign=0, ellipsize=3)
            labels.append(name)
            detail = Gtk.Label(label=('已隐藏 · ' if entry.hidden else '') + ('用户自定义' if entry.user else '系统应用'), xalign=0)
            detail.add_css_class('dim-label')
            detail.add_css_class('caption')
            labels.append(detail)
            box.append(labels)
            row.set_child(box)
            self.listbox.append(row)
            self.rows.append(row)
        self.loading = False
        self.dirty = False
        self.save_button.set_sensitive(False)
        self.stack.set_visible_child_name('empty')
        self.filter_rows()
        if selected_id:
            for row in self.rows:
                if row.entry.desktop_id == selected_id:
                    self.listbox.select_row(row)
                    break
        if self.store.errors:
            self.toast(f'跳过 {len(self.store.errors)} 个无法读取的启动项')

    def filter_rows(self):
        query = self.search.get_text().casefold()
        category = CATEGORIES[self.category.get_selected()][1]
        count = 0
        for row in getattr(self, 'rows', []):
            entry = row.entry
            matches = query in (entry.name + ' ' + get(entry.keyfile, 'Exec') + ' ' + entry.desktop_id).casefold()
            matches = matches and (not category or category in get(entry.keyfile, 'Categories').split(';'))
            row.set_visible(matches)
            count += bool(matches)
        self.count.set_label(f'{count} 个应用' if count else '没有匹配的应用')

    def selected(self, _listbox, row):
        if self.loading or row is None or row.entry is self.current:
            return
        target = row.entry
        # Restore highlight while asking about unsaved changes.
        self.loading = True
        self.listbox.unselect_all()
        for previous in self.rows:
            if previous.entry is self.current:
                self.listbox.select_row(previous)
        self.loading = False
        self.guard(lambda: self.show_entry(target))

    def show_entry(self, entry):
        self.loading = True
        self.current = entry
        self.force_exec = False
        self.heading.set_label(entry.name)
        for key, field in self.fields.items():
            field.set_text(get(entry.keyfile, key, localized=key in {'Name', 'Comment'}))
        self.terminal.set_active(boolean(entry.keyfile, 'Terminal'))
        self.visible.set_active(not entry.hidden)
        self.source.set_label(('用户启动项：' if entry.user else '系统启动项（保存为用户覆盖）：') + str(entry.path))
        self.remove_button.set_sensitive(entry.user and entry.path.exists())
        self.listbox.unselect_all()
        for row in self.rows:
            if row.entry.desktop_id == entry.desktop_id:
                self.listbox.select_row(row)
                break
        self.stack.set_visible_child_name('editor')
        self.loading = False
        self.dirty = False
        self.save_button.set_sensitive(False)

    def new_entry(self):
        self.show_entry(self.store.new())
        self.changed()
        self.fields['Name'].grab_focus()

    def no_sandbox(self, *_):
        try:
            field = self.fields['Exec']
            command = add_no_sandbox(field.get_text())
            if command == field.get_text():
                self.toast('已包含参数；保存后将确保通过此命令启动')
            else:
                field.set_text(command)
                self.toast('已添加参数；点击保存后生效')
            self.force_exec = True
            self.changed()
        except ValueError as error:
            self.toast(str(error))

    def save(self):
        if self.current is None:
            return False
        try:
            values = {key: field.get_text() for key, field in self.fields.items()}
            categories = values['Categories'].strip().strip(';')
            values['Categories'] = categories + ';' if categories else ''
            values.update(Terminal=self.terminal.get_active(), NoDisplay=not self.visible.get_active())
            if self.force_exec:
                values['DBusActivatable'] = False
            entry = self.store.save(self.current, values)
            self.reload(entry.desktop_id)
            self.toast('已保存，GNOME 应用菜单会自动更新')
            return True
        except (ValueError, OSError, GLib.Error) as error:
            self.toast('保存失败：' + str(error))
            return False

    def remove(self, *_):
        entry = self.current
        if entry is None:
            return
        dialog = Adw.AlertDialog(heading='删除这个用户启动项？', body='若存在同名系统启动项，将恢复系统默认。自定义启动项会从菜单中移除；应用本身不会被卸载。')
        dialog.add_response('cancel', '取消')
        dialog.add_response('delete', '删除')
        dialog.set_response_appearance('delete', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response('cancel')
        def responded(_dialog, response):
            if response == 'delete':
                try:
                    self.store.remove_override(entry)
                    self.reload(entry.desktop_id)
                    self.toast('已删除用户启动项')
                except (ValueError, OSError) as error:
                    self.toast(str(error))
        dialog.connect('response', responded)
        dialog.present(self)


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        window = self.props.active_window or Window(self)
        window.present()


if __name__ == '__main__':
    raise SystemExit(Application().run(sys.argv))
