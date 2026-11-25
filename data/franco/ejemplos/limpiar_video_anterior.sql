-- Las corridas anteriores no identificaban su fuente. Se exige un lote completo
-- de tres carriles por tres clases en el intervalo que el usuario confirmó.
WITH candidatos AS (
    SELECT *
    FROM conteos
    WHERE interseccion = 'DEMO_INT_01' AND prueba AND origen_demo IS NULL
      AND inicio >= :'video_desde'::timestamptz
      AND inicio < :'video_desde'::timestamptz + interval '1 second'
      AND fin >= :'video_hasta'::timestamptz
      AND fin < :'video_hasta'::timestamptz + interval '1 second'
), lote AS (
    SELECT inicio, fin, acceso
    FROM candidatos
    GROUP BY inicio, fin, acceso
    HAVING count(*) = 9
       AND count(DISTINCT carril) = 3
       AND count(DISTINCT (carril, clase)) = 9
), eliminados AS (
    DELETE FROM conteos c
    USING candidatos x, lote
    WHERE (SELECT count(*) FROM lote) = 1
      AND (x.inicio, x.fin, x.acceso) = (lote.inicio, lote.fin, lote.acceso)
      AND (c.mensaje_id, c.inicio) = (x.mensaje_id, x.inicio)
    RETURNING 1
)
SELECT 'CYSA_VIDEO_ELIMINADAS=' || count(*) AS resultado
FROM eliminados;
