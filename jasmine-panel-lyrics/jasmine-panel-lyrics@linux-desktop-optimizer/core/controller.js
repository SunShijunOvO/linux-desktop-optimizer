import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

export function trackKey(state) {
    return JSON.stringify(state ? [state.player, state.id, state.url, state.title, state.artist] : null);
}

// Owns synchronization only; neither the panel nor player-specific API logic lives here.
export class LyricsController {
    constructor({reader, providers, onUpdate, now = () => GLib.get_monotonic_time() / 1000}) {
        this._reader = reader;
        this._providers = providers;
        this._onUpdate = onUpdate;
        this._now = now;
        this._alive = true;
        this._busy = false;
        this._version = 0;
        this._state = null;
        this._key = null;
        this._entries = [];
        this._source = '';
        this._retryAt = Infinity;
        this._attempt = 0;
    }

    start() {
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
            void this.tick();
            return GLib.SOURCE_CONTINUE;
        });
        void this.tick();
    }

    async tick() {
        if (!this._alive || this._busy)
            return;
        this._busy = true;
        try {
            const state = await this._reader.read();
            if (!this._alive)
                return;
            this._state = state;
            const key = trackKey(state);
            if (key !== this._key) {
                this._key = key;
                this._reset();
                if (state)
                    void this._load(false);
            } else if (state && this._now() >= this._retryAt) {
                void this._load(false);
            }
            this._emit();
        } catch (error) {
            if (this._alive) {
                this._state = null;
                this._key = null;
                this._reset();
                this._source = `播放器暂不可用：${error.message}`;
                this._emit();
            }
        } finally {
            this._busy = false;
        }
    }

    _reset() {
        this._version++;
        this._cancel?.cancel();
        this._cancel = null;
        this._entries = [];
        this._source = this._state ? '正在加载歌词…' : '';
        this._retryAt = Infinity;
        this._attempt = 0;
    }

    reload() {
        if (!this._alive)
            return;
        this._reset();
        if (this._state)
            void this._load(true);
        this._emit();
    }

    async _load(refresh) {
        const version = ++this._version;
        this._cancel?.cancel();
        const cancellable = new Gio.Cancellable();
        this._cancel = cancellable;
        this._retryAt = Infinity;
        this._attempt++;
        const state = this._state;
        const errors = [];
        let result = {entries: [], source: '暂无歌词'};
        for (const provider of this._providers) {
            if (!provider.supports(state))
                continue;
            try {
                result = await provider.load(state, cancellable, {refresh});
            } catch (error) {
                errors.push(`${provider.id}：${error.message}`);
            }
            if (!this._alive || version !== this._version)
                return;
            if (result.entries.length)
                break;
        }
        this._entries = result.entries;
        this._source = result.source;
        if (errors.length && !result.entries.length) {
            // Retry transient failures, but never poll the lyric endpoint continuously.
            if (this._attempt < 4)
                this._retryAt = this._now() + 5000 * 2 ** (this._attempt - 1);
            this._source = `${errors.join('；')} · ${this._attempt < 4 ? '稍后重试' : '可点击重新加载'}`;
        }
        this._emit();
    }

    _emit() {
        if (this._alive)
            this._onUpdate({state: this._state, entries: this._entries, source: this._source});
    }

    destroy() {
        this._alive = false;
        if (this._timer)
            GLib.Source.remove(this._timer);
        this._timer = null;
        this._reset();
        this._reader.destroy();
        for (const provider of this._providers)
            provider.destroy?.();
        this._onUpdate = null;
        this._state = null;
    }
}
