FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# gcc/build-essential: pyswisseph builds a C extension from source.
# The rest are Playwright/Chromium's runtime shared-library dependencies
# on Debian slim (no X server, so these are the headless subset).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Downloads Chromium into the image; runtime OS deps are already installed above.
RUN playwright install chromium

COPY app ./app

EXPOSE 8000

# Shell form (not exec array) so ${PORT} expands: Render injects its own PORT
# at runtime, defaulting to 8000 for local docker-compose where it's unset.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
