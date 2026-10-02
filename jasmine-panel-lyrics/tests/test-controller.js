import GLib from 'gi://GLib';
import {LyricsController} from '../jasmine-panel-lyrics@linux-desktop-optimizer/core/controller.js';

function check(condition, message) { if (!condition) throw new Error(message); }
function flush() {
    return new Promise(resolve => GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
        resolve(); return GLib.SOURCE_REMOVE;
    }));
}
const track = title => ({player: 'test', id: title, title, artist: '', url: '', position: 1200, status: 'Playing'});
let state = track('A');
let snapshot;
let clock = 0;
const pending = [];
let destroyed = false;
const provider = {
    id: 'test', supports: () => true,
    load: (_state, cancel) => new Promise(resolve => pending.push({resolve, cancel})),
};
const controller = new LyricsController({
    reader: {read: async () => state, destroy() { destroyed = true; }},
    providers: [provider], now: () => clock, onUpdate: value => { snapshot = value; },
});
const lyrics = text => ({entries: [{time: 1000, text}], source: 'test'});
await controller.tick();
state = {...state, position: 8000};
await controller.tick();
check(snapshot.state.position === 8000, 'Slow lyric requests must not block progress');
state = track('B');
await controller.tick();
check(pending[0].cancel.is_cancelled(), 'Track change cancels previous request');
pending[1].resolve(lyrics('B'));
await flush();
pending[0].resolve(lyrics('A'));
await flush();
check(snapshot.entries[0].text === 'B', 'Late response must not overwrite the current song');
controller.reload();
check(snapshot.entries.length === 0 && pending.length === 3, 'Reload starts a fresh request');
controller.destroy();
pending[2].resolve(lyrics('late'));
await flush();
check(destroyed && pending[2].cancel.is_cancelled(), 'Disable destroys reader and cancels requests');
check(snapshot.entries.length === 0, 'Disabled controller does not update panel');

let calls = 0;
let recovered = false;
const retry = new LyricsController({
    reader: {read: async () => track('retry'), destroy() {}},
    providers: [{id: 'remote', supports: () => true, async load() {
        calls++;
        if (!recovered) throw new Error('offline');
        return lyrics('recovered');
    }}, {id: 'local', supports: () => true, async load() { return {entries: [], source: 'none'}; }}],
    now: () => clock, onUpdate: value => { snapshot = value; },
});
await retry.tick(); await flush();
for (let i = 0; i < 10; i++) await retry.tick();
check(calls === 1, 'No HTTP storm after failure');
clock = 5000;
await retry.tick(); await flush();
check(calls === 2, 'Retry after backoff');
recovered = true;
clock = 15000;
await retry.tick(); await flush();
check(snapshot.entries[0].text === 'recovered', 'Service recovery updates lyrics');
retry.destroy();

const fallback = new LyricsController({
    reader: {read: async () => track('local'), destroy() {}},
    providers: [{id: 'remote', supports: () => true, async load() { throw new Error('offline'); }},
        {id: 'local', supports: () => true, async load() { return lyrics('local fallback'); }}],
    onUpdate: value => { snapshot = value; },
});
await fallback.tick(); await flush();
check(snapshot.entries[0].text === 'local fallback', 'Local lyrics work when remote provider fails');
fallback.destroy();
print('Controller concurrency, stale response, cancellation, retry and fallback tests passed');
