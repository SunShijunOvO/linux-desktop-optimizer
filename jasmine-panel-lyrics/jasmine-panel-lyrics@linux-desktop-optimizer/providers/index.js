import {YesPlayMusicProvider} from './yesplaymusic.js';
import {LocalLyricsProvider} from './local.js';

// Ordered providers: dedicated integrations first, generic local LRC last.
export function createProviders(http) {
    return [new YesPlayMusicProvider(http), new LocalLyricsProvider()];
}
