@echo off
title StockPro - Serveur de developpement
echo ============================================
echo   StockPro - MediCare Industries
echo   Demarrage du serveur Django...
echo ============================================
echo.
call venv\Scripts\activate
python manage.py runserver
pause
