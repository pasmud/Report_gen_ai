from .models import Question
import chromadb
from django.conf import settings
from chromadb.utils import embedding_functions
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=str(settings.CHROMADB_PERSIST_DIRECTORY))

def get_embedding_function():
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.OPENAI_API_KEY,
        model_name="text-embedding-3-small"
    )

def get_chroma_collection(project_id):
    collection_name = f'project_{project_id}'
    try:
        return chroma_client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
    except ValueError as e:
        logger.error(f"Collection {collection_name} does not exist: {e}")
        raise

def retrieve_relevant_chunks(question):
    try:
        collection = get_chroma_collection(question.project.id)
        results = collection.query(
            query_texts=[question.text],
            n_results=5
        )
        return [metadata['chunk'] for metadata in results['metadatas'][0]]
    except Exception as e:
        logger.error(f"Error retrieving chunks for question {question.id}: {e}")
        raise

def generate_answer(question_text, chunks):
    context = "\n".join(chunks)
    try:
        response = openai_client.chat.completions.create(
            model='gpt-4',
            messages=[
                {'role': 'system', 'content': 'You are an assistant that provides detailed answers.'},
                {'role': 'user', 'content': f'Context: {context}\n\nQuestion: {question_text}'}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        raise

def answer_question(question):
    try:
        relevant_chunks = retrieve_relevant_chunks(question)
        answer = generate_answer(question.text, relevant_chunks)
        logger.info(f"Generated answer for question {question.id}")
        return answer
    except ValueError as e:
        logger.warning(f"Collection not found for question {question.id}: {e}")
        return "Documents are still being processed or collection does not exist. Please try again later."
    except Exception as e:
        logger.error(f"Error answering question {question.id}: {e}")
        return "An error occurred while processing your question. Please try again later."