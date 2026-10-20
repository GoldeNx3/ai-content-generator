FROM php:8.4-cli-trixie AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends git unzip libpq-dev libicu-dev libzip-dev \
        python3 python3-venv \
    && docker-php-ext-install pdo_pgsql pcntl intl bcmath zip \
    && pecl install redis \
    && docker-php-ext-enable redis \
    && rm -rf /var/lib/apt/lists/* /tmp/pear

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

ENV AI_PYTHON=/opt/ai/bin/python \
    AI_WORKDIR=/srv/ai \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY api/requirements-ai.txt /tmp/requirements-ai.txt
RUN python3 -m venv /opt/ai \
    && /opt/ai/bin/pip install --no-cache-dir -r /tmp/requirements-ai.txt pytest==8.4.2 pytest-asyncio==1.2.0

WORKDIR /srv/platform

FROM base AS app

COPY platform/composer.json platform/composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist --no-interaction

COPY platform/ ./
COPY api/ /srv/ai/
RUN composer dump-autoload --optimize --no-dev \
    && chown -R www-data:www-data storage bootstrap/cache

EXPOSE 8000

CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]
