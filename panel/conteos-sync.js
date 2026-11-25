export function pollCountRevision(url, refresh, read = fetch) {
    let seen;
    let checking = false;
    return async () => {
        if (checking) return;
        checking = true;
        try {
            const response = await read(url, {cache: 'no-store'});
            if (!response.ok) return;
            const {revision} = await response.json();
            if (typeof revision === 'string' && revision !== seen && await refresh()) {
                seen = revision;
            }
        } catch {
            // Un reinicio del panel se recupera en la siguiente consulta.
        } finally {
            checking = false;
        }
    };
}
