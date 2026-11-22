const views = new Set(['conteos', 'inventario', 'estados', 'usuarios', 'configuraciones', 'planes', 'reportes']);

export function panelView(location) {
    const id = new URLSearchParams(location.search).get('modulo') || location.hash.slice(1);
    return views.has(id) ? id : 'conteos';
}

export function serviceUrl(config, key, path) {
    const base = config[key];
    if (!base) throw new Error('El servicio todavía no está preparado. Inicia CYSA.');
    let url;
    try { url = new URL(base); } catch { throw new Error('La dirección local del servicio no es válida.'); }
    if (!['http:', 'https:'].includes(url.protocol)
        || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
        || url.username || url.password || url.search || url.hash
        || (url.pathname !== '/' && url.pathname !== '')) {
        throw new Error('La dirección local del servicio no es válida.');
    }
    return url.origin + path;
}
