FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VAT_GUI_HOST=0.0.0.0 \
    VAT_GUI_PORT=7860 \
    VAT_GUI_OPEN_BROWSER=0

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["python", "gui.py"]
