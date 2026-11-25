WITH eliminados AS (
    DELETE FROM conteos
    WHERE origen_demo = 'video'
       OR (origen_demo IS NULL AND interseccion = 'DEMO_VIDEO' AND prueba)
    RETURNING 1
)
SELECT format('Filas de video eliminadas: %s.', count(*)) AS resultado
FROM eliminados;
