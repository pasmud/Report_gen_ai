from celery import shared_task
from .document_processing import process_document

@shared_task
def process_document_task(document_id):
    from .models import Document
    document = Document.objects.get(id=document_id)
    print('document')
    process_document(document)
