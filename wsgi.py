import sys
import os

# Pad naar het project toevoegen
path = '/home/DanielK06/12Build-Project'
if path not in sys.path:
    sys.path.insert(0, path)

# .env laden
from dotenv import load_dotenv
load_dotenv(os.path.join(path, '.env'))

# Database initialiseren bij eerste start
from database import init_db, laad_mock_data
init_db()
laad_mock_data()

from app import app as application
