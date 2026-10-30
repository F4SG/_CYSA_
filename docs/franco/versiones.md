# Versiones fijadas y compatibilidad
Objetivo Python 3.12. Pruebas ejecutadas con el runtime Python 3.12 disponible en este entorno.
- FastAPI 0.136.0; Pydantic 2.11.4; Uvicorn 0.34.2; Paho MQTT 2.1.0.
- Psycopg/binary 3.2.9; PyJWT/crypto 2.15.1. Criptografía transitiva se registra en el informe de pruebas.
- PyYAML 6.0.2; pytest 8.3.5; httpx 0.28.1.
- Detección: Ultralytics 8.4.63 con YOLO26n, OpenCV 4.11.0.86 y lap 0.5.12. No ejecutados con cámara en este entorno.
- SUMO, sumolib y sumo-data 1.27.0. Sin TraCI ni panel de simulación.
- Imágenes de referencia: Python 3.12.10-slim, TimescaleDB 2.19.3-pg17, Mosquitto 2.0.21,
  Keycloak 26.8.1, Nginx 1.30.6-alpine. Variables de imagen en .env permiten adaptar previa verificación.

**Desviaciones explícitas del Perfil:** se propone PG17 con TimescaleDB 2.19.3 y Mosquitto 2.0.21 como base
concreta de laboratorio, en lugar de afirmar verificados PG18.6 y Mosquitto 2.1.2. La imagen final y su disponibilidad
no pudieron probarse sin Docker. Antes de integrar S0, confirmar sus versiones y elegir una combinación soportada;
si el equipo exige las versiones del Perfil, ajustar imágenes y repetir migración, TLS e integración. No migrar a ciegas.
El panel es HTML/CSS/JS sin librerías CDN. El flujo OIDC se implementa con Web Crypto/Fetch estándar.
Las versiones directas se fijan; las dependencias transitivas pueden variar al instalar en otra fecha. El informe
incluye las versiones efectivamente cargadas al probar. No se declara certificado el conjunto de contenedores.
