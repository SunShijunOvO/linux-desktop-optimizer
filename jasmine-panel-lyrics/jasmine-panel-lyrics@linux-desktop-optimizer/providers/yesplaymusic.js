import {parseLrc} from '../core/lyrics.js';

export class YesPlayMusicProvider {
    constructor(http, {playerUrl = 'http://127.0.0.1:27232/player',
        lyricUrl = 'http://127.0.0.1:10754/lyric'} = {}) {
        this.id = 'yesplaymusic';
        this._http = http;
        this._playerUrl = playerUrl;
        this._lyricUrl = lyricUrl;
        this._cache = new Map();
    }

    supports(state) {
        return /^org\.mpris\.MediaPlayer2\.yesplaymusic(?:\.|$)/i.test(state.player);
    }

    async load(state, cancellable, {refresh = false} = {}) {
        // mpris:trackid is a playlist index in YesPlayMusic, NOT a NetEase ID.
        let id = state.url.match(/^\/trackid\/(\d+)$/)?.[1];
        if (!id) {
            const data = await this._http.getJson(this._playerUrl, cancellable);
            const track = data?.currentTrack;
            const artist = track?.ar?.map(item => item.name).join(', ');
            // Do not attach the next song's lyrics to stale MPRIS metadata.
            if (!track || !state.title || track.name !== state.title ||
                (state.artist && artist !== state.artist))
                throw new Error('YesPlayMusic 歌曲信息正在同步');
            id = String(track.id);
        }
        if (!/^[1-9]\d*$/.test(id))
            throw new Error('YesPlayMusic 未提供有效歌曲 ID');
        if (refresh)
            this._cache.delete(id);
        if (this._cache.has(id)) {
            const cached = this._cache.get(id);
            this._cache.delete(id);
            this._cache.set(id, cached);
            return cached;
        }
        const data = await this._http.getJson(`${this._lyricUrl}?id=${encodeURIComponent(id)}`, cancellable);
        if (data?.code !== 200)
            throw new Error(`YesPlayMusic 歌词接口错误（${data?.code ?? '无状态码'}）`);
        const text = data?.lrc?.lyric;
        if (text !== undefined && typeof text !== 'string')
            throw new Error('YesPlayMusic 歌词格式无效');
        const entries = parseLrc(text ?? '');
        const result = {entries, source: entries.length ? `YesPlayMusic · ${id}` : 'YesPlayMusic 暂无逐行歌词'};
        if (!cancellable.is_cancelled()) {
            this._cache.set(id, result);
            if (this._cache.size > 32)
                this._cache.delete(this._cache.keys().next().value);
        }
        return result;
    }

    destroy() {
        this._cache.clear();
    }
}
