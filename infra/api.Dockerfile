FROM python:3.12.10-slim
WORKDIR /workspace
COPY backend/requirements.txt /tmp/requirements.txt
COPY simulacion/requirements.txt /tmp/simulacion.txt
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.2 && pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/simulacion.txt && useradd --uid 10001 --create-home cysa
COPY shared /workspace/shared
COPY backend /workspace/backend
COPY inventario /workspace/inventario
COPY operacion /workspace/operacion
COPY controlador /workspace/controlador
COPY simulacion /workspace/simulacion
COPY tools/franco /workspace/tools
ENV PYTHONPATH=/workspace:/workspace/shared:/workspace/backend:/workspace/inventario:/workspace/controlador:/workspace/simulacion
USER cysa
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
