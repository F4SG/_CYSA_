-- El segundo filtro identifica filas de versiones anteriores por su UUID exacto.
DELETE FROM conteos
WHERE origen_demo = 'practica'
   OR (origen_demo IS NULL AND prueba AND interseccion = 'DEMO_INT_01'
       AND acceso IN ('N', 'S', 'E', 'W') AND carril = acceso || '_0'
       AND mensaje_id = md5('cysa-practica-v1:' || extract(epoch FROM inicio)::bigint
                            || ':' || acceso || ':' || clase)::uuid);
