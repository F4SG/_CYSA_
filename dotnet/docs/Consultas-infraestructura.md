# Consultar infraestructura del corredor

En **Gestionar infraestructura**, seleccionar un recurso y usar **Aplicar filtros**.
La búsqueda y los filtros se combinan antes de paginar. **Limpiar filtros** vuelve a
la primera página; cambiar de recurso también elimina los filtros anteriores.
Los nombres de los casos de uso permanecen iguales al modelo.

Los GET de corredores, intersecciones, accesos, carriles, fuentes de detección y
controladores aceptan `buscar` (hasta 120 caracteres) y `corredorId`.
Todos salvo corredores aceptan `interseccionId`. Accesos, carriles y fuentes
aceptan `accesoId`. Solo fuentes de detección acepta `activa=true|false`.
Los filtros por IDs recorren las relaciones, sin depender de coincidencias de nombres.

Ejemplo: `GET /api/fuentes-deteccion?corredorId=1&interseccionId=1&activa=true&pagina=1&tamano=15`.
Los IDs deben ser positivos. Un padre inexistente devuelve una lista vacía (200).
Un filtro que no corresponde al recurso devuelve 400; no se ignora silenciosamente.
La búsqueda es por texto literal contenido, con la intercalación de SQL Server;
los valores se parametrizan mediante EF Core. No admite expresiones SQL ni comodines.
El orden es por ID ascendente y los permisos existentes se conservan.

`Probar-WebIII.py` verifica filtros combinados, paginación, resultados vacíos,
estado inactivo y consultas incorrectas contra SQL Server real.
