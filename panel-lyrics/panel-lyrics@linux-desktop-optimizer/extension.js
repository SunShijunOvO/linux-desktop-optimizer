import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {parseLrc, lyricAt, safeFilename} from './lyrics.js';
import {PlayerReader} from './player.js';

export default class PanelLyrics extends Extension {
    enable() {
        this._generation = (this._generation ?? 0) + 1;
        this._reader = new PlayerReader();
        this._fileCancel = new Gio.Cancellable();
        this._busy = false;
        this._key = null;
        this._entries = [];
        this._state = null;
        this._lyricsDirectory = GLib.build_filenamev([
            GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC) ??
                GLib.build_filenamev([GLib.get_home_dir(), 'Music']), 'Lyrics',
        ]);
        this._button = new PanelMenu.Button(0.0, 'Panel Lyrics');
        this._label = new St.Label({
            text: '♫ 等待播放器', y_align: Clutter.ActorAlign.CENTER,
            style_class: 'panel-lyrics-label',
        });
        this._label.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        this._button.add_child(this._label);
        this._details = new PopupMenu.PopupMenuItem('等待播放器', {reactive: false});
        this._button.menu.addMenuItem(this._details);
        this._fileInfo = new PopupMenu.PopupMenuItem('本地 LRC 歌词', {reactive: false});
        this._button.menu.addMenuItem(this._fileInfo);
        const reload = new PopupMenu.PopupMenuItem('重新加载歌词');
        reload.connect('activate', () => { this._key = null; });
        this._button.menu.addMenuItem(reload);
        Main.panel.addToStatusArea(this.uuid, this._button, 0, 'right');
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
            this._tick();
            return GLib.SOURCE_CONTINUE;
        });
        this._tick();
    }

    async _tick() {
        if (this._busy)
            return;
        this._busy = true;
        const generation = this._generation;
        try {
            const state = await this._reader.read();
            if (generation !== this._generation)
                return;
            this._state = state;
            const key = JSON.stringify(state ? [state.player, state.id, state.url,
                state.title, state.artist] : null);
            if (key !== this._key) {
                this._key = key;
                this._entries = [];
                this._render();
                await this._loadLyrics(state, generation);
            }
            if (generation === this._generation)
                this._render();
        } catch (error) {
            if (generation === this._generation) {
                this._state = null;
                this._key = null;
                this._entries = [];
                this._render();
                this._details.label.text = `播放器暂不可用：${error.message}`;
            }
        } finally {
            if (generation === this._generation)
                this._busy = false;
        }
    }

    async _loadLyrics(state, generation) {
        this._fileInfo.label.text = '未找到本地 LRC（放入音乐目录的 Lyrics 文件夹）';
        if (!state)
            return;
        const candidates = [];
        if (state.url.startsWith('file://')) {
            const path = Gio.File.new_for_uri(state.url).get_path();
            if (path) {
                const dot = path.lastIndexOf('.');
                const stem = dot > path.lastIndexOf('/') ? path.slice(0, dot) : path;
                candidates.push(`${stem}.lrc`);
            }
        }
        if (state.title) {
            if (state.artist)
                candidates.push(GLib.build_filenamev([this._lyricsDirectory,
                    `${safeFilename(state.artist)} - ${safeFilename(state.title)}.lrc`]));
            candidates.push(GLib.build_filenamev([this._lyricsDirectory,
                `${safeFilename(state.title)}.lrc`]));
        }
        for (const path of [...new Set(candidates)]) {
            try {
                const bytes = await new Promise((resolve, reject) => {
                    Gio.File.new_for_path(path).load_contents_async(this._fileCancel, (file, result) => {
                        try {
                            const [, contents] = file.load_contents_finish(result);
                            resolve(contents);
                        } catch (error) {
                            reject(error);
                        }
                    });
                });
                if (generation !== this._generation)
                    return;
                this._entries = parseLrc(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
                this._fileInfo.label.text = this._entries.length ? path : `无有效时间戳：${path}`;
                return;
            } catch (error) {
                if (generation !== this._generation)
                    return;
                if (!error.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.NOT_FOUND)) {
                    this._fileInfo.label.text = `歌词读取失败：${path}`;
                    return;
                }
            }
        }
    }

    _render() {
        const state = this._state;
        if (!state) {
            this._label.text = '♫ 等待播放器';
            this._details.label.text = '等待支持 MPRIS 的播放器';
            return;
        }
        const song = [state.artist, state.title].filter(Boolean).join(' - ') || '未知歌曲';
        this._details.label.text = `${song} · ${state.player.replace('org.mpris.MediaPlayer2.', '')}`;
        if (state.status === 'Stopped') {
            this._label.text = '♫ 已停止';
            return;
        }
        const lyric = state.position === null ? '' : lyricAt(this._entries, state.position);
        this._label.text = `${state.status === 'Paused' ? '⏸' : '♫'} ${lyric || song}`;
        if (state.position === null)
            this._details.label.text += ' · 播放器未提供进度';
    }

    disable() {
        this._generation++;
        if (this._timer)
            GLib.Source.remove(this._timer);
        this._timer = null;
        this._reader?.destroy();
        this._reader = null;
        this._fileCancel?.cancel();
        this._fileCancel = null;
        this._button?.destroy();
        this._button = null;
        this._label = null;
        this._details = null;
        this._fileInfo = null;
        this._entries = [];
        this._state = null;
    }
}
