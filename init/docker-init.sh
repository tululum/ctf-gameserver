#!/usr/bin/env bash
set -eu

echo "- Sleeping for 5 seconds..."
sleep 5

export PYTHONPATH=/etc/ctf-gameserver/web
echo "- [DJANGO] Make migrations..."
django-admin makemigrations --settings prod_settings templatetags registration scoring flatpages
echo "- [DJANGO] Migrate..."
django-admin migrate --settings prod_settings


if [[ "$(psql "$PGHOST" -U ctf-gameserver -d ctf-gameserver -tAq -c "select exists (select from pg_matviews  where matviewname  like 'scoring_%')")" == "f" ]]; then
    echo "- Initializing scoring materialized view..."
    psql -h "$PGHOST" -U ctf-gameserver -d ctf-gameserver < /scoring.sql
fi

if [[ "$(psql "$PGHOST" -U ctf-gameserver -d ctf-gameserver -tAq -c "select exists (select from pg_matviews  where matviewname  like 'scoreboard_v2_%')")" == "f" ]]; then
    echo "- Initializing scoreboard_v2 materialized view..."
    psql -h "$PGHOST" -U ctf-gameserver -d ctf-gameserver < /scoreboard_v2.sql
fi

if [[ "$(psql "$PGHOST" -U ctf-gameserver -d ctf-gameserver -tAq -c "select count(*) from scoring_service")" == "0" ]]; then
    cd /ansible
    echo "- Initializing database with Ansible..."
    ansible-playbook -i /ansible/hosts gamedb-import.yaml
fi
