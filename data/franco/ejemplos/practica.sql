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
