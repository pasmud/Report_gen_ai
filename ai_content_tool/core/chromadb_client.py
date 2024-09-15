# core/chromadb_client.py

import chromadb
from django.conf import settings as django_settings

client = chromadb.Client(
    persist_directory=str(django_settings.CHROMADB_PERSIST_DIRECTORY)
)
