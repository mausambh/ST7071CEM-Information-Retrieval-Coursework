@echo off

REM Move to the Django coursework project directory.
cd /d "C:\Users\mausa\OneDrive\Dokumente\Class (Masters)\Information Retrieval\Python\ST7071CEM_IR\assignment"

REM Use the coursework virtual environment to run the repeatable
REM crawler and search-index update command.
"C:\Users\mausa\OneDrive\Dokumente\Class (Masters)\Information Retrieval\Python\.venv\Scripts\python.exe" manage.py update_search_index