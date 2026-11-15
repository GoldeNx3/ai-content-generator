FROM php:8.4-fpm-trixie AS base

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

COPY ai/requirements.txt /tmp/requirements-ai.txt
RUN python3 -m venv /opt/ai \
    && /opt/ai/bin/pip install --no-cache-dir --upgrade pip==26.3 \
    && /opt/ai/bin/pip install --no-cache-dir -r /tmp/requirements-ai.txt

WORKDIR /srv/platform

FROM base AS dev

RUN /opt/ai/bin/pip install --no-cache-dir pytest==9.2.0 pytest-asyncio==1.5.0 \
    && python3 -m venv /opt/audit \
    && /opt/audit/bin/pip install --no-cache-dir pip-audit==2.10.1

CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]

FROM base AS app

COPY platform/composer.json platform/composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist --no-interaction

COPY platform/ ./
COPY ai/ /srv/ai/
RUN composer dump-autoload --optimize --no-dev \
    && chown -R www-data:www-data storage bootstrap/cache

COPY platform/docker/php-fpm.conf /usr/local/etc/php-fpm.d/zz-platform.conf

USER www-data

EXPOSE 9000

CMD ["php-fpm"]
