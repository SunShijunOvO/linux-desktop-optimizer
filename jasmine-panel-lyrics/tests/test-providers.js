import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Soup from 'gi://Soup?version=3.0';
import {HttpClient} from '../jasmine-panel-lyrics@linux-desktop-optimizer/transport/http.js';
import {YesPlayMusicProvider} from '../jasmine-panel-lyrics@linux-desktop-optimizer/providers/yesplaymusic.js';

function check(condition, message) { if (!condition) throw new Error(message); }
async function rejects(action, message) {
    let failed = false;
    try { await action(); } catch { failed = true; }
    check(failed, message);
}
let count = 0;
let mode = 'normal';
let requestedId;
const server = new Soup.Server();
server.add_handler(null, (_server, message, path, query) => {
    count++;
    if (mode === 'http-error') {
        message.set_status(503, null);
        return;
    }
    if (mode === 'timeout') {
        message.pause();
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2000, () => {
            message.set_status(504, null);
            message.unpause();
            return GLib.SOURCE_REMOVE;
        });
        return;
    }
    const body = path === '/player'
        ? {currentTrack: {id: 123, name: 'Song', ar: [{name: 'Artist'}]}}
        : {code: mode === 'api-error' ? 500 : 200,
            lrc: {lyric: mode === 'no-lyrics' ? '' : '[00:01]first\n[00:03]second'}};
    requestedId = query?.id ?? requestedId;
    message.set_status(200, null);
    message.set_response('application/json', Soup.MemoryUse.COPY,
        mode === 'malformed' ? '{broken' : mode === 'large' ? 'x'.repeat(4096) : JSON.stringify(body));
});
server.listen_local(0, Soup.ServerListenOptions.IPV4_ONLY);
const base = `http://127.0.0.1:${server.get_uris()[0].get_port()}`;
const http = new HttpClient({maxBytes: 1024, timeout: 1});
const provider = new YesPlayMusicProvider(http, {playerUrl: `${base}/player`, lyricUrl: `${base}/lyric`});
const cancel = new Gio.Cancellable();
const state = {player: 'org.mpris.MediaPlayer2.yesplaymusic', id: '/track/8',
    title: 'Song', artist: 'Artist', url: '/trackid/456'};
try {
    check(provider.supports(state), 'Match YesPlayMusic');
    check(!provider.supports({...state, player: 'org.mpris.MediaPlayer2.vlc'}), 'Do not query YesPlayMusic for another player');
    let result = await provider.load(state, cancel);
    check(result.entries.length === 2 && requestedId === '456', 'Use xesam:url, never playlist index');
    const beforeCache = count;
    await provider.load(state, cancel);
    check(count === beforeCache, 'Cache hit makes no HTTP request');
    await provider.load(state, cancel, {refresh: true});
    check(count === beforeCache + 1, 'Manual reload invalidates cache');
    await provider.load({...state, url: ''}, cancel);
    check(requestedId === '123', 'Legacy /player fallback resolves NetEase ID');
    await rejects(() => provider.load({...state, title: 'Other', url: ''}, cancel),
        'Reject /player metadata from a different track');
    for (const failure of ['http-error', 'api-error', 'malformed', 'large', 'timeout']) {
        mode = failure;
        await rejects(() => provider.load(state, cancel, {refresh: true}), `Handle ${failure}`);
    }
    mode = 'no-lyrics';
    result = await provider.load(state, cancel, {refresh: true});
    check(result.entries.length === 0, 'Instrumental / missing lyrics is not an error');
    mode = 'normal';
    const cancelled = new Gio.Cancellable();
    cancelled.cancel();
    await rejects(() => provider.load(state, cancelled, {refresh: true}), 'Cancellation stops HTTP');
    print('YesPlayMusic HTTP, ID matching, cache, refresh, error, timeout and cancellation tests passed');
} finally {
    provider.destroy();
    http.destroy();
    server.disconnect();
}
