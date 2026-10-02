// Optional read-only check against an already running YesPlayMusic desktop app.
import GLib from 'gi://GLib';
import {PlayerReader} from '../jasmine-panel-lyrics@linux-desktop-optimizer/players/mpris.js';
import {createProviders} from '../jasmine-panel-lyrics@linux-desktop-optimizer/providers/index.js';
import {HttpClient} from '../jasmine-panel-lyrics@linux-desktop-optimizer/transport/http.js';
import {LyricsController} from '../jasmine-panel-lyrics@linux-desktop-optimizer/core/controller.js';
const http = new HttpClient();
const providers = createProviders(http);
let timer;
let controller;
try {
    const result = await new Promise((resolve, reject) => {
        controller = new LyricsController({
            reader: new PlayerReader({priority: name => providers.findIndex(p => p.supports({player: name}))}),
            providers,
            onUpdate: snapshot => {
                if (snapshot.source.startsWith('YesPlayMusic · ') && snapshot.entries.length)
                    resolve({source: snapshot.source, lines: snapshot.entries.length,
                        status: snapshot.state.status, position: snapshot.state.position});
            },
        });
        timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 15000, () => {
            timer = null;
            reject(new Error('No synchronized YesPlayMusic lyrics within 15 seconds'));
            return GLib.SOURCE_REMOVE;
        });
        controller.start();
    });
    print(JSON.stringify(result));
} finally {
    if (timer) GLib.Source.remove(timer);
    controller?.destroy();
    http.destroy();
}
