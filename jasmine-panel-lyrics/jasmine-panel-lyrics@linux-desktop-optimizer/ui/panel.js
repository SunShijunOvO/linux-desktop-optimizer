import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {lyricAt} from '../core/lyrics.js';

export class LyricsPanel {
    constructor(uuid, onReload) {
        this._button = new PanelMenu.Button(0.0, 'jasmine-panel-lyrics');
        this._label = new St.Label({
            text: '♫ 等待播放器', y_align: Clutter.ActorAlign.CENTER,
            style_class: 'jasmine-panel-lyrics-label',
        });
        this._label.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        this._button.add_child(this._label);
        this._details = new PopupMenu.PopupMenuItem('等待播放器', {reactive: false});
        this._button.menu.addMenuItem(this._details);
        this._source = new PopupMenu.PopupMenuItem('歌词来源', {reactive: false});
        this._button.menu.addMenuItem(this._source);
        const reload = new PopupMenu.PopupMenuItem('重新加载歌词');
        reload.connect('activate', onReload);
        this._button.menu.addMenuItem(reload);
        Main.panel.addToStatusArea(uuid, this._button, 0, 'right');
    }

    update({state, entries, source}) {
        this._source.label.text = source || '支持 YesPlayMusic 自动歌词和本地 LRC';
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
        const lyric = state.position === null ? '' : lyricAt(entries, state.position);
        this._label.text = `${state.status === 'Paused' ? '⏸' : '♫'} ${lyric || song}`;
        if (state.position === null)
            this._details.label.text += ' · 播放器未提供进度';
    }

    destroy() {
        this._button.destroy();
    }
}
