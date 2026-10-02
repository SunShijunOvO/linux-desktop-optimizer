import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Soup from 'gi://Soup?version=3.0';

// Bounded asynchronous requests. Local player endpoints bypass desktop proxies.
export class HttpClient {
    constructor({timeout = 5, maxBytes = 2 * 1024 * 1024} = {}) {
        this._session = new Soup.Session({
            timeout, proxy_resolver: Gio.SimpleProxyResolver.new(null, null),
        });
        this._maxBytes = maxBytes;
    }

    async getJson(url, cancellable) {
        const message = Soup.Message.new('GET', url);
        message.set_flags(Soup.MessageFlags.NO_REDIRECT);
        const stream = await new Promise((resolve, reject) => {
            this._session.send_async(message, GLib.PRIORITY_DEFAULT, cancellable, (session, result) => {
                try { resolve(session.send_finish(result)); } catch (error) { reject(error); }
            });
        });
        try {
            if (message.status_code !== 200)
                throw new Error(`HTTP ${message.status_code}`);
            const chunks = [];
            let length = 0;
            while (true) {
                const bytes = await new Promise((resolve, reject) => {
                    stream.read_bytes_async(16384, GLib.PRIORITY_DEFAULT, cancellable, (input, result) => {
                        try { resolve(input.read_bytes_finish(result)); } catch (error) { reject(error); }
                    });
                });
                const data = bytes.get_data();
                if (!data.length)
                    break;
                length += data.length;
                if (length > this._maxBytes)
                    throw new Error('响应超过大小限制');
                chunks.push(data);
            }
            const buffer = new Uint8Array(length);
            let offset = 0;
            for (const chunk of chunks) {
                buffer.set(chunk, offset);
                offset += chunk.length;
            }
            return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(buffer));
        } finally {
            stream.close_async(GLib.PRIORITY_DEFAULT, null, (input, result) => {
                try { input.close_finish(result); } catch { /* request already closed */ }
            });
        }
    }

    destroy() {
        this._session.abort();
    }
}
