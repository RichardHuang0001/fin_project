#!/usr/bin/env bash
set -euo pipefail
mkdir -p /root/autodl-tmp/fin/{services,config,logs,run,models,ops}
mkdir -p /root/autodl-tmp/fin/ops/{env_templates,deploy,systemd,docs}
mkdir -p /root/autodl-tmp/fin/logs/{fin_agent,fin_data_svr,fin_llm}
if [ ! -e /srv/fin ]; then
  mkdir -p /srv
  ln -s /root/autodl-tmp/fin /srv/fin
fi
