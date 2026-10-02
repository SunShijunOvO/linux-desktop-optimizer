import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {parseLrc, safeFilename} from '../core/lyrics.js';

export class LocalLyricsProvider {
    constructor() {
        this.id = 'local';
        this._directory = GLib.build_filenamev([
            GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC) ??
                GLib.build_filenamev([GLib.get_home_dir(), 'Music']), 'Lyrics',
        ]);
    }

    supports(_state) {
        return true;
    }

    async load(state, cancellable) {
        const candidates = [];
        if (state.url.startsWith('file://')) {
            const path = Gio.File.new_for_uri(state.url).get_path();
            if (path) {
                const dot = path.lastIndexOf('.');
                candidates.push(`${dot > path.lastIndexOf('/') ? path.slice(0, dot) : path}.lrc`);
            }
        }
        if (state.title) {
            if (state.artist)
                candidates.push(GLib.build_filenamev([this._directory,
                    `${safeFilename(state.artist)} - ${safeFilename(state.title)}.lrc`]));
            candidates.push(GLib.build_filenamev([this._directory, `${safeFilename(state.title)}.lrc`]));
        }
        for (const path of [...new Set(candidates)]) {
            try {
                const bytes = await new Promise((resolve, reject) => {
                    Gio.File.new_for_path(path).load_contents_async(cancellable, (file, result) => {
                        try { resolve(file.load_contents_finish(result)[1]); } catch (error) { reject(error); }
                    });
                });
                const entries = parseLrc(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
                return {entries, source: entries.length ? path : `无有效时间戳：${path}`};
            } catch (error) {
                if (cancellable.is_cancelled())
                    throw error;
                if (!error.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.NOT_FOUND))
                    throw new Error(`歌词读取失败：${path}`);
            }
        }
        return {entries: [], source: '未找到本地 LRC（放入音乐目录的 Lyrics 文件夹）'};
    }
}
