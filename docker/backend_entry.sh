#!/bin/bash
# set -e

. /appenv/bin/activate

exec "$@" /var/log/log.log

