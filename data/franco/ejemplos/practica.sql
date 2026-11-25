INSERT INTO inventario (activo_id, interseccion, acceso, tipo, ubicacion, protocolo, prueba)
SELECT activo_id, 'DEMO_INT_01', acceso, tipo, ubicacion, protocolo, true
FROM (VALUES
    ('DEMO_INT_01', NULL, 'interseccion', 'UBICACION_SINTETICA', 'no_aplica'),
    ('DEMO_ACCESO_N', 'N', 'acceso', 'UBICACION_SINTETICA', 'no_aplica'),
    ('DEMO_ACCESO_S', 'S', 'acceso', 'UBICACION_SINTETICA', 'no_aplica'),
    ('DEMO_ACCESO_E', 'E', 'acceso', 'UBICACION_SINTETICA', 'no_aplica'),
    ('DEMO_ACCESO_W', 'W', 'acceso', 'UBICACION_SINTETICA', 'no_aplica'),
    ('DEMO_CAM_01', 'N', 'camara', 'WEBCAM_DE_PRUEBA', 'USB'),
    ('DEMO_CTL_01', NULL, 'controlador', 'CONTROLADOR_FICTICIO', 'MQTT_TLS')
) AS activos(activo_id, acceso, tipo, ubicacion, protocolo)
ON CONFLICT (activo_id) DO NOTHING;

-- Muestras sintéticas de los últimos 288 bloques de cinco minutos.
WITH ventanas AS (
    SELECT date_bin('5 minutes', now(), TIMESTAMPTZ '2000-01-01 00:00:00+00')
           - tramo * interval '5 minutes' AS inicio, tramo
    FROM generate_series(1, 288) AS serie(tramo)
), demanda AS (
    SELECT ventanas.*, extract(hour FROM inicio AT TIME ZONE 'America/La_Paz')::integer AS hora
    FROM ventanas
)
INSERT INTO conteos (mensaje_id, interseccion, acceso, carril, clase, cantidad, inicio, fin, prueba, origen_demo)
SELECT md5('cysa-practica-v2:' || extract(epoch FROM inicio)::bigint || ':' || carril || ':' || clase)::uuid,
       'DEMO_INT_01', acceso, carril, clase,
       greatest(0, base + CASE WHEN hora IN (7, 8, 12, 13, 17, 18, 19) THEN punta
                              WHEN hora < 6 OR hora >= 22 THEN valle ELSE 0 END
                       + ((tramo * 7 + variacion) % amplitud) - amplitud / 2),
       inicio, inicio + interval '30 seconds', true, 'practica'
FROM demanda
CROSS JOIN (VALUES ('N','N_0',1), ('N','N_1',3), ('N','N_2',5),
                   ('S','S_0',7), ('E','E_0',9), ('W','W_0',11)) AS carriles(acceso,carril,variacion)
CROSS JOIN (VALUES ('auto', 6, 4, -4, 5), ('moto', 3, 2, -2, 5),
                   ('micro', 1, 1, -1, 3)) AS clases(clase,base,punta,valle,amplitud)
ON CONFLICT (mensaje_id, inicio) DO NOTHING;
