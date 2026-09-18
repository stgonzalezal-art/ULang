FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 PORT=7860
EXPOSE 7860

# Arranque combinado (servidor + trabajador en un hilo), ideal para un
# servicio gratuito que da un solo contenedor. Para separarlos:
#   docker run ... python servidor.py
#   docker run ... python trabajador.py --intervalo 3600
CMD ["python", "huggingface.py"]
