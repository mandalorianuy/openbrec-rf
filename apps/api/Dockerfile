FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/openbrec:/opt/openbrec/apps/api:/opt/openbrec/apps/fusion-worker

RUN pip install --no-cache-dir \
    fastapi==0.139.2 \
    jsonschema[format]==4.26.0 \
    paho-mqtt==2.1.0 \
    uvicorn==0.51.0

RUN useradd --create-home --uid 10001 openbrec
WORKDIR /opt/openbrec
COPY --chown=openbrec:openbrec openbrec ./openbrec
COPY --chown=openbrec:openbrec schemas ./schemas
COPY --chown=openbrec:openbrec apps/api ./apps/api
COPY --chown=openbrec:openbrec apps/fusion-worker ./apps/fusion-worker
USER openbrec

CMD ["uvicorn", "openbrec_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
