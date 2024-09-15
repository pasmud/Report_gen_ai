from cgitb import text
from .models import Document
from openai import OpenAI
import chromadb
from django.conf import settings as django_settings
import os
from chromadb.utils import embedding_functions


# client = chromadb.Client(
#     persist_directory=str(django_settings.CHROMADB_PERSIST_DIRECTORY)
# )

def process_document(document):
    import os
    
    print(f"chunks len")
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    # Extract text
    text = extract_text_from_file(document.file.path)
    if not text:
        return
    # Split text
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(text)
    print(f"chunks len={len(chunks)}")
    # Generate embeddings
    embeddings = generate_embeddings(chunks)
    # Store in ChromaDB
    store_embeddings(document.project.id, chunks, embeddings)

def extract_text_from_file(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    if extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif extension in ['.doc', '.docx']:
        return extract_text_from_docx(file_path)
    else:
        raise ValueError('Unsupported file type')

def extract_text_from_pdf(file_path):
    from PyPDF2 import PdfReader
    text = ""
    reader = PdfReader(file_path)
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file_path):
    import docx
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def generate_embeddings(chunks):
    embeddings = []
    # openai.api_key = django_settings.OPENAI_API_KEY
    
    
    for chunk in chunks:
        
        response = get_embedding(text=chunk)

        # response = client.embeddings.create(
        #     input=chunk,
        #     model='text-embedding-ada-002'
        # )
        embeddings.append(response)
        
        # embeddings = df.combined.apply(lambda x: get_embedding(x, model='text-embedding-ada-002'))
    return embeddings

def get_embedding(text, model="text-embedding-3-small"):
    client = OpenAI(api_key=django_settings.OPENAI_API_KEY,)
    text = text.replace("\n", " ")
    return client.embeddings.create(input = [text], model=model).data[0].embedding



def store_embeddings(project_id, chunks, embeddings):
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=django_settings.OPENAI_API_KEY,
                model_name="text-embedding-3-small"
            )
    # client = chromadb.Client()
    client = chromadb.PersistentClient(path=str(django_settings.CHROMADB_PERSIST_DIRECTORY))
    collection_name = f'project_{project_id}'
    collection = client.get_or_create_collection(name=collection_name,embedding_function=openai_ef)
    collection.add(
        embeddings=embeddings,
        metadatas=[{'chunk': chunk} for chunk in chunks],
        ids=[str(i) for i in range(len(chunks))]
    )
