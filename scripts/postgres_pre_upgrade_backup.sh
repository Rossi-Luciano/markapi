#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/local.yml}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-postgres}"
ARCHIVE_ROOT="${ARCHIVE_ROOT:-${ROOT_DIR}/../scms_data/markapi/postgres_backups_pre_upgrade}"
TIMESTAMP="$(date +'%Y_%m_%dT%H_%M_%S')"
ARCHIVE_DIR="${ARCHIVE_ROOT}/${TIMESTAMP}"

cd "${ROOT_DIR}"

if ! docker compose -f "${COMPOSE_FILE}" ps --status running "${COMPOSE_SERVICE}" 2>/dev/null | grep -q "${COMPOSE_SERVICE}"; then
    echo "Serviço ${COMPOSE_SERVICE} não está em execução. Suba o stack: docker compose -f ${COMPOSE_FILE} up -d ${COMPOSE_SERVICE}"
    exit 1
fi

echo "A criar backup lógico (pg_dump) no contentor ${COMPOSE_SERVICE}..."
docker compose -f "${COMPOSE_FILE}" exec -T "${COMPOSE_SERVICE}" backup

mkdir -p "${ARCHIVE_DIR}"
BACKUP_VOLUME="${BACKUP_VOLUME:-../scms_data/markapi/data_dev_backup}"

if [[ -d "${ROOT_DIR}/${BACKUP_VOLUME}" ]]; then
    shopt -s nullglob
    backups=("${ROOT_DIR}/${BACKUP_VOLUME}"/backup_*.sql.gz)
    shopt -u nullglob
    if [[ ${#backups[@]} -eq 0 ]]; then
        echo "Nenhum ficheiro backup_*.sql.gz em ${ROOT_DIR}/${BACKUP_VOLUME}"
        exit 1
    fi
    latest_backup="$(ls -t "${backups[@]}" | head -1)"
    cp -a "${latest_backup}" "${ARCHIVE_DIR}/"
    cp -a "${latest_backup}" "${ARCHIVE_ROOT}/latest_pre_upgrade.sql.gz"
    echo "Cópia de segurança: ${ARCHIVE_DIR}/$(basename "${latest_backup}")"
    echo "Atalho: ${ARCHIVE_ROOT}/latest_pre_upgrade.sql.gz"
else
    echo "Volume de backups não encontrado (${ROOT_DIR}/${BACKUP_VOLUME}). O dump foi criado no contentor em /backups."
fi

echo "Concluído. Antes de subir Postgres 18, pare django/celery e siga docs/ops/postgres-upgrade-backup.md"
