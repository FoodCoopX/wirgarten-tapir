#!/bin/sh
# Roles of the Tapir production image: web | worker | beat | manage <args> | migrate | <command>
set -e

for dir in media filepond_temp_uploads filepond_stored_uploads emails_from_celery log; do
    mkdir -p "/data/$dir"
done

case "${1:-web}" in
    web)
        exec gunicorn tapir.wsgi:application --bind "${GUNICORN_BIND:-0.0.0.0:8000}" \
            --workers "${GUNICORN_WORKERS:-3}" --access-logfile - ;;
    worker)
        exec celery -A tapir worker -l info ;;
    beat)
        exec celery -A tapir beat -l info --schedule /data/celerybeat-schedule ;;
    migrate)
        python manage.py migrate --noinput
        exec python manage.py parameter_definitions ;;
    manage)
        shift
        exec python manage.py "$@" ;;
    *)
        exec "$@" ;;
esac
