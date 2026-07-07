#!/bin/bash
cd "$(dirname "$0")"
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./run.sh"'
