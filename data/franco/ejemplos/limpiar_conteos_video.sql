WITH eliminados AS (
    DELETE FROM conteos
    WHERE origen_demo = 'video'
       OR (origen_demo IS NULL AND interseccion = 'DEMO_VIDEO' AND prueba)
    RETURNING 1
)
SELECT 'CYSA_VIDEO_ELIMINADAS=' || count(*) AS resultado
FROM eliminados;
