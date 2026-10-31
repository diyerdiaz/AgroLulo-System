#!/bin/sh
# Arranca como root solo para dejarle al usuario de la app las carpetas que
# Docker monta desde el servidor (nacen de root y SQLite no podría escribir
# ahí). Después la app corre sin privilegios, como el usuario agrolulo.
set -e

if [ "$(id -u)" = "0" ]; then
    chown -R agrolulo:agrolulo /app/instance /app/app/static/uploads
    exec setpriv --reuid=agrolulo --regid=agrolulo --clear-groups "$@"
fi

exec "$@"
