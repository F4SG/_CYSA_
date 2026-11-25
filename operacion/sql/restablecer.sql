IF DB_NAME() <> N'CYSA_Control_S2'
    THROW 51000, 'El restablecimiento solo se aplica a CYSA_Control_S2.', 1;

DELETE FROM control_envios;
DELETE FROM control_decisiones;
TRUNCATE TABLE control_auditoria;
DELETE FROM control_planes;
TRUNCATE TABLE control_conteos;
TRUNCATE TABLE control_estados;
