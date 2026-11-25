import assert from 'node:assert/strict';
import {test} from 'node:test';
import {pollCountRevision} from '../../panel/conteos-sync.js';

test('la vista vuelve a consultar después de importar o borrar y reintenta si está ocupada', async () => {
    let revision = 'inicio';
    let busy = false;
    const refreshes = [];
    const poll = pollCountRevision('/runtime/conteos.json',
        () => {
            if (busy) return false;
            refreshes.push(revision);
            return true;
        },
        async (url, options) => {
            assert.equal(url, '/runtime/conteos.json');
            assert.equal(options.cache, 'no-store');
            return {ok: true, json: async () => ({revision})};
        });

    await poll();
    revision = 'video-importado';
    await poll();
    revision = 'video-eliminado';
    busy = true;
    await poll();
    assert.deepEqual(refreshes, ['inicio', 'video-importado']);
    busy = false;
    await poll();
    await poll();
    assert.deepEqual(refreshes, ['inicio', 'video-importado', 'video-eliminado']);
});
