#!/bin/bash

echo -e "\033[32mStarting development servers...\033[0m"

echo -e "\033[33mOpening database proxy in new terminal window...\033[0m"
osascript -e 'tell application "Terminal" to do script "flyctl proxy 15432:5432 -a small-night-2462"'

echo -e "\033[33mOpening backend server in new terminal window...\033[0m"
osascript -e 'tell application "Terminal" to do script "cd EquityAlchemy && source venv/bin/activate && cd backend && python -m uvicorn entrypoints.backend:app --reload"'

echo -e "\033[33mOpening frontend server in new terminal window...\033[0m"
    osascript -e 'tell application "Terminal" to do script "cd EquityAlchemy/frontend; npm start"'

echo -e "\033[32mAll servers are starting in separate terminal windows.\033[0m"
echo -e "\033[36mPress any key to exit this script...\033[0m"
read -n 1 -s
