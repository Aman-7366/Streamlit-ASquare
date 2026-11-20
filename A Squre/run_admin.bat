@echo off
cd /d "%~dp0"
REM Admin runs only on this computer (localhost), not visible to the internet/customers
streamlit run admin.py --server.port 8502 --server.address localhost
