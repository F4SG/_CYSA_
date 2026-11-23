BEGIN;

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

-- Muestras de 30 segundos cada media hora. Un intervalo repetido conserva su ID.
WITH ventanas AS (
    SELECT date_bin('30 minutes', now() - interval '30 seconds', TIMESTAMPTZ '2000-01-01 00:00:00+00')
           - tramo * interval '30 minutes' AS inicio
    FROM generate_series(0, 47) AS serie(tramo)
)
INSERT INTO conteos (mensaje_id, interseccion, acceso, carril, clase, cantidad, inicio, fin, prueba)
SELECT md5('cysa-practica-v1:' || extract(epoch FROM inicio)::bigint || ':' || acceso || ':' || clase)::uuid,
       'DEMO_INT_01', acceso, acceso || '_0', clase,
       base + ((extract(epoch FROM inicio)::bigint / 1800 + variacion) % amplitud)::integer,
       inicio, inicio + interval '30 seconds', true
FROM ventanas
CROSS JOIN (VALUES ('N', 1), ('S', 3), ('E', 5), ('W', 7)) AS accesos(acceso, variacion)
CROSS JOIN (VALUES ('auto', 5, 8), ('moto', 1, 5), ('micro', 0, 3)) AS clases(clase, base, amplitud)
ON CONFLICT (mensaje_id, inicio) DO NOTHING;

COMMIT;
