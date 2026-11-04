#!/bin/bash
# Первичная установка на Ubuntu 22.04/24.04 (Timeweb Cloud). Запуск: root.
set -euo pipefail

REPO="${PES_DATA_REPO:-https://github.com/k53303325-max/pes-data.git}"
APP_DIR=/opt/pes-data

apt update
apt install -y git python3 python3-venv python3-pip nginx certbot python3-certbot-nginx

if ! id pesdata &>/dev/null; then
  adduser --disabled-password --gecos "" pesdata
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO" "$APP_DIR"
  chown -R pesdata:pesdata "$APP_DIR"
fi

su - pesdata -c "cd $APP_DIR && python3 -m venv venv && ./venv/bin/pip install -U pip && ./venv/bin/pip install -r requirements.txt"

cp "$APP_DIR/deploy/systemd/pes-data-admin.service" /etc/systemd/system/
cp "$APP_DIR/deploy/systemd/pes-data-poller.service" /etc/systemd/system/
systemctl daemon-reload

if [[ ! -f /etc/pes-data.env ]]; then
  cp "$APP_DIR/deploy/timeweb.env.example" /etc/pes-data.env
  chmod 600 /etc/pes-data.env
  echo "Заполните /etc/pes-data.env (DATABASE_URL, BOT_TOKEN, APP_URL, ADMIN_*)."
fi

if [[ -f "$APP_DIR/deploy/nginx/pes-data.conf.example" ]]; then
  cp "$APP_DIR/deploy/nginx/pes-data.conf.example" /etc/nginx/sites-available/pes-data
  ln -sf /etc/nginx/sites-available/pes-data /etc/nginx/sites-enabled/pes-data
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx
fi

echo "Готово. nano /etc/pes-data.env && systemctl enable --now pes-data-admin pes-data-poller"
