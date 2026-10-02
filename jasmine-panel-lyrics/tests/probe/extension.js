// Installed only inside the smoke test's temporary headless desktop.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class Probe extends Extension {
    enable() {
        const root = GLib.get_user_cache_dir();
        this._remote = GLib.getenv('JASMINE_SMOKE_MODE') === '--yesplay';
        const audio = `${root}/song.ogg`;
        GLib.file_set_contents(`${root}/song.lrc`, '[00:01]第一句\n[00:03]第二句');
        this._position = 1500000;
        this._status = 'Playing';
        this._title = '测试歌曲';
        this._url = this._remote ? '/trackid/123' : Gio.File.new_for_path(audio).get_uri();
        GLib.file_set_contents(`${root}/remote.lrc`, '[00:01]第一句\n[00:03]第二句');
        const probe = this;
        this._service = Gio.DBusExportedObject.wrapJSObject(`<node>
            <interface name="org.mpris.MediaPlayer2.Player">
            <property name="Metadata" type="a{sv}" access="read"/>
            <property name="Position" type="x" access="read"/>
            <property name="PlaybackStatus" type="s" access="read"/>
            </interface></node>`, {
            get Metadata() {
                return {
                    'mpris:trackid': new GLib.Variant('o', '/track/1'),
                    'xesam:title': new GLib.Variant('s', probe._title),
                    'xesam:url': new GLib.Variant('s', probe._url),
                };
            },
            get Position() { return probe._position; },
            get PlaybackStatus() { return probe._status; },
        });
        this._service.export(Gio.DBus.session, '/org/mpris/MediaPlayer2');
        this._owner = Gio.bus_own_name(Gio.BusType.SESSION,
            this._remote ? 'org.mpris.MediaPlayer2.yesplaymusic' : 'org.mpris.MediaPlayer2.PanelLyricsProbe',
            Gio.BusNameOwnerFlags.NONE,
            null, () => this._run(root), null);
    }

    _run(root) {
        let step = 0;
        const stages = [
            ['♫ 第一句', () => { this._status = 'Paused'; }],
            ['⏸ 第一句', () => { this._status = 'Playing'; this._position = 3500000; }],
            ['♫ 第二句', () => { this._position = 1500000; }],
            ['♫ 第一句', () => {
                GLib.file_set_contents(`${root}/${this._remote ? 'remote' : 'song'}.lrc`, '[00:01]已重新加载');
                const button = Main.panel.statusArea['jasmine-panel-lyrics@linux-desktop-optimizer'];
                button.menu._getMenuItems()[2].emit('activate', null);
            }],
            ['♫ 已重新加载', () => { this._title = '无歌词测试'; this._url = this._remote ? '/trackid/456' : ''; }],
            ['♫ 无歌词测试', () => { this._status = 'Stopped'; }],
            ['♫ 已停止', () => {}],
        ];
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, () => {
            try {
                const button = Main.panel.statusArea['jasmine-panel-lyrics@linux-desktop-optimizer'];
                const text = button.get_children()[0].text;
                const [expected, next] = stages[step];
                if (text !== expected)
                    throw new Error(`Step ${step}: expected ${expected}, got ${text}`);
                next();
                step++;
                if (step < stages.length)
                    return GLib.SOURCE_CONTINUE;
                GLib.file_set_contents(`${root}/probe-result`, 'PASS');
            } catch (error) {
                GLib.file_set_contents(`${root}/probe-result`, `FAIL: ${error.message}`);
            }
            this._timer = null;
            return GLib.SOURCE_REMOVE;
        });
    }

    disable() {
        if (this._timer)
            GLib.Source.remove(this._timer);
        this._timer = null;
        Gio.bus_unown_name(this._owner);
        this._service.unexport();
        this._service = null;
    }
}
