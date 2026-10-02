import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const PLAYER = 'org.mpris.MediaPlayer2.Player';
const PATH = '/org/mpris/MediaPlayer2';

function unpack(value) {
    if (value instanceof GLib.Variant)
        return unpack(value.deepUnpack());
    if (Array.isArray(value))
        return value.map(unpack);
    if (value && typeof value === 'object')
        return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, unpack(item)]));
    return value;
}

// One active player, one outstanding request. Polling Position also handles seeking
// in players which omit Seeked signals. All bus operations are asynchronous.
export class PlayerReader {
    constructor({priority = () => 0} = {}) {
        this._priority = priority;
        this._cancel = new Gio.Cancellable();
        this._name = null;
        this._owner = null;
    }

    _call(name, path, iface, method, parameters, signature) {
        return new Promise((resolve, reject) => {
            Gio.DBus.session.call(name, path, iface, method, parameters,
                new GLib.VariantType(signature), Gio.DBusCallFlags.NONE, 1500,
                this._cancel, (connection, result) => {
                    try {
                        resolve(unpack(connection.call_finish(result)));
                    } catch (error) {
                        reject(error);
                    }
                });
        });
    }

    async read() {
        try {
            if (!this._name) {
                const [names] = await this._call('org.freedesktop.DBus',
                    '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'ListNames', null, '(as)');
                this._name = names.filter(name => name.startsWith('org.mpris.MediaPlayer2.')).sort((a, b) => this._priority(a) - this._priority(b) || a.localeCompare(b))[0];
                if (!this._name)
                    return null;
                [this._owner] = await this._call('org.freedesktop.DBus',
                    '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'GetNameOwner',
                    new GLib.Variant('(s)', [this._name]), '(s)');
            }
            const [properties] = await this._call(this._owner, PATH,
                'org.freedesktop.DBus.Properties', 'GetAll',
                new GLib.Variant('(s)', [PLAYER]), '(a{sv})');
            const metadata = properties.Metadata ?? {};
            return {
                player: this._name,
                id: metadata['mpris:trackid'] ?? '',
                title: metadata['xesam:title'] ?? '',
                artist: (metadata['xesam:artist'] ?? []).join(', '),
                url: metadata['xesam:url'] ?? '',
                status: properties.PlaybackStatus ?? 'Stopped',
                position: Number.isFinite(properties.Position) ? properties.Position / 1000 : null,
            };
        } catch (error) {
            this._name = null;
            this._owner = null;
            if (!this._cancel.is_cancelled())
                throw error;
            return null;
        }
    }

    destroy() {
        this._cancel.cancel();
    }
}
