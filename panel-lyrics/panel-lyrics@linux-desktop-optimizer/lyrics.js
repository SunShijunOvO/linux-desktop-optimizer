// Pure parsing and lookup logic, shared by the extension and its tests.
export function parseLrc(source) {
    const entries = [];
    let offset = 0;
    for (const line of source.replace(/^\uFEFF/, '').split(/\r?\n/)) {
        const adjustment = line.match(/^\s*\[offset:([+-]?\d+)\]\s*$/i);
        if (adjustment) {
            offset = Number(adjustment[1]);
            continue;
        }
        const timestamps = [...line.matchAll(/\[(\d+):([0-5]\d)(?:\.(\d{1,3}))?\]/g)];
        if (!timestamps.length)
            continue;
        const last = timestamps[timestamps.length - 1];
        const text = line.slice(last.index + last[0].length).trim();
        for (const stamp of timestamps) {
            entries.push({
                time: Number(stamp[1]) * 60000 + Number(stamp[2]) * 1000 +
                    Number((stamp[3] ?? '').padEnd(3, '0')),
                text,
            });
        }
    }
    // Positive LRC offset means display the lyrics earlier.
    return entries.map(entry => ({...entry, time: entry.time - offset}))
        .sort((a, b) => a.time - b.time);
}

export function lyricAt(entries, milliseconds) {
    let low = 0;
    let high = entries.length;
    while (low < high) {
        const middle = (low + high) >>> 1;
        if (entries[middle].time <= milliseconds)
            low = middle + 1;
        else
            high = middle;
    }
    return low ? entries[low - 1].text : '';
}

export function safeFilename(text) {
    return text.replace(/[\/\\\x00-\x1f]/g, '_').trim();
}
