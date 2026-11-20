FROM python:3.12.10-slim
WORKDIR /workspace
COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.2 && pip install --no-cache-dir -r /tmp/requirements.txt && useradd --uid 10001 --create-home cysa
COPY shared /workspace/shared
COPY backend /workspace/backend
COPY inventario /workspace/inventario
COPY tools/franco /workspace/tools
ENV PYTHONPATH=/workspace/shared:/workspace/backend:/workspace/inventario
USER cysa
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
