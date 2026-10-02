import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {LyricsController} from './core/controller.js';
import {PlayerReader} from './players/mpris.js';
import {createProviders} from './providers/index.js';
import {HttpClient} from './transport/http.js';
import {LyricsPanel} from './ui/panel.js';

export default class JasminePanelLyrics extends Extension {
    enable() {
        this._http = new HttpClient();
        const providers = createProviders(this._http);
        this._panel = new LyricsPanel(this.uuid, () => this._controller.reload());
        this._controller = new LyricsController({
            reader: new PlayerReader({
                priority: name => providers.findIndex(provider => provider.supports({player: name})),
            }),
            providers,
            onUpdate: snapshot => this._panel.update(snapshot),
        });
        this._controller.start();
    }

    disable() {
        this._controller?.destroy();
        this._controller = null;
        this._http?.destroy();
        this._http = null;
        this._panel?.destroy();
        this._panel = null;
    }
}
