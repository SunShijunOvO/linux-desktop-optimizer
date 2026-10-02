import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {PlayerReader} from '../jasmine-panel-lyrics@linux-desktop-optimizer/players/mpris.js';
const xml = `<node><interface name="org.mpris.MediaPlayer2.Player">
<property name="Metadata" type="a{sv}" access="read"/>
<property name="Position" type="x" access="read"/>
<property name="PlaybackStatus" type="s" access="read"/>
</interface></node>`;
let position = 1250000;
let status = 'Playing';
let title = '测试歌曲';
const service = Gio.DBusExportedObject.wrapJSObject(xml, {
    get Metadata() {
        return {
            'mpris:trackid': new GLib.Variant('o', '/track/1'),
            'xesam:title': new GLib.Variant('s', title),
            'xesam:artist': new GLib.Variant('as', ['歌手']),
            'xesam:url': new GLib.Variant('s', 'file:///tmp/test.ogg'),
        };
    },
    get Position() { return position; },
    get PlaybackStatus() { return status; },
});
const reader = new PlayerReader();
function check(condition, message) {
    if (!condition)
        throw new Error(message);
}
let owner;
try {
    check(await reader.read() === null, 'No player must return null');
    service.export(Gio.DBus.session, '/org/mpris/MediaPlayer2');
    await new Promise(resolve => {
        owner = Gio.bus_own_name(Gio.BusType.SESSION, 'org.mpris.MediaPlayer2.PanelLyricsTest',
            Gio.BusNameOwnerFlags.NONE, null, resolve, null);
    });
    let state = await reader.read();
    check(state.title === title && state.artist === '歌手' && state.position === 1250,
        'Read and unpack metadata; convert microseconds to milliseconds');
    status = 'Paused';
    state = await reader.read();
    check(state.status === 'Paused' && state.position === 1250, 'Pause keeps position');
    status = 'Playing';
    position = 9000000;
    check((await reader.read()).position === 9000, 'Forward seek');
    position = 500000;
    check((await reader.read()).position === 500, 'Backward seek');
    title = '下一首';
    check((await reader.read()).title === title, 'Track changes');
    status = 'Stopped';
    check((await reader.read()).status === 'Stopped', 'Stopped state');
    service.unexport();
    let failed = false;
    try { await reader.read(); } catch { failed = true; }
    check(failed, 'Player disappearance must clear connection and report error');
    service.export(Gio.DBus.session, '/org/mpris/MediaPlayer2');
    check((await reader.read()).title === title, 'Reconnect after disappearance');
    reader.destroy();
    check(await reader.read() === null, 'Cancellation does not leak an error');
    print('MPRIS integration assertions passed');
} finally {
    reader.destroy();
    service.unexport();
    if (owner)
        Gio.bus_unown_name(owner);
}
