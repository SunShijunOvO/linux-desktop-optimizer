import {parseLrc, lyricAt, safeFilename} from '../panel-lyrics@linux-desktop-optimizer/lyrics.js';

let count = 0;
function equal(actual, expected) {
    count++;
    if (JSON.stringify(actual) !== JSON.stringify(expected))
        throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}
const entries = parseLrc('\uFEFF[ti:Example]\r\n[00:02.50][00:04.005]重复\r\n[00:01.1]开始\n[00:03]');
equal(entries, [
    {time: 1100, text: '开始'}, {time: 2500, text: '重复'},
    {time: 3000, text: ''}, {time: 4005, text: '重复'},
]);
equal(lyricAt(entries, 1099), '');
equal(lyricAt(entries, 1100), '开始');
equal(lyricAt(entries, 2999), '重复');
equal(lyricAt(entries, 3000), '');
equal(lyricAt(entries, 9000), '重复');
equal(lyricAt(entries, 1200), '开始'); // backwards seek
// Offset can be declared after timestamps, and negative offsets delay lyrics.
equal(parseLrc('[00:01]早\n[offset:+500]'), [{time: 500, text: '早'}]);
equal(parseLrc('[offset:-250]\n[00:01]晚'), [{time: 1250, text: '晚'}]);
equal(parseLrc('[00:99]无效\n[ar:歌手]\nplain'), []);
equal(lyricAt([], 1), '');
equal(safeFilename(' a/b\\c\u0000 '), 'a_b_c_');
print(`${count} LRC assertions passed`);
