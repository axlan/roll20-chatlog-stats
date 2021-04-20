#!/usr/bin/env bash

cd /home/axlan/src/roll20-chatlog-stats
source .env/bin/activate
gunicorn --bind 0.0.0.0:8181 dashboard:server
