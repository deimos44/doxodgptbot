services:
  - type: web
    name: doxodgptbot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python finance_bot.py
    autoDeploy: true
