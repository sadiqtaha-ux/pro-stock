@echo off
title Pro-Stock - Serveur de developpement
echo ============================================
echo   Pro-Stock - MediCare Industries
echo   Demarrage du serveur Django...
echo ============================================
echo.
call venv\Scripts\activate
python manage.py runserver
pause
