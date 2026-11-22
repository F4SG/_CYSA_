import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';

const source = await readFile(new URL('../../panel/navigation.js', import.meta.url), 'utf8');
const {panelView, serviceUrl} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));

test('las opciones del proyecto seleccionan vistas del mismo panel', () => {
    for (const hash of ['#configuraciones', '#planes', '#reportes', '#estados']) {
        assert.equal(panelView({hash, search: ''}), hash.slice(1));
    }
    assert.equal(panelView({hash: '#swagger', search: ''}), 'conteos');
});

test('las direcciones antiguas abren la vista que corresponde', () => {
    assert.equal(panelView({hash: '', search: '?modulo=configuraciones&volver=1'}), 'configuraciones');
    assert.equal(panelView({hash: '', search: '?modulo=planes&volver=1'}), 'planes');
});

test('los módulos consultan los puertos configurados', () => {
    const config = {webApiBase: 'http://localhost:25183/', operacionBase: 'http://localhost:25184'};
    assert.equal(serviceUrl(config, 'webApiBase', '/api/proyecto/configuraciones'), 'http://localhost:25183/api/proyecto/configuraciones');
    assert.equal(serviceUrl(config, 'operacionBase', '/api/operacion/planes'), 'http://localhost:25184/api/operacion/planes');
});

test('se rechazan direcciones incompletas o ajenas a la instalación local', () => {
    assert.throws(() => serviceUrl({}, 'webApiBase', '/api/proyecto/configuraciones'), /no está preparado/);
    for (const value of ['https://example.com', 'javascript:alert(1)', 'http://usuario:clave@localhost:15184', 'http://localhost:15184/otro']) {
        assert.throws(() => serviceUrl({operacionBase: value}, 'operacionBase', '/api/estados'), /no es válida/);
    }
});
