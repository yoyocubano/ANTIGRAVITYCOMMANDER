web: cd backend && gunicorn -k gthread --threads 100 -w 1 dashboard_server:app --bind 0.0.0.0:$PORT
worker: cd backend && python master_coordinator.py
