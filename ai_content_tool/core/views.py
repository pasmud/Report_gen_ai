# core/views.py

from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.contrib.auth.models import User

from .models import Project, Document, Question
from .serializers import (
    ProjectSerializer,
    DocumentSerializer,
    QuestionSerializer,
    RegisterSerializer,
    AnswerSerializer
)
from .document_processing import process_document
from .question_answering import answer_question
from .tasks import process_document_task

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response



# Registration View
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]  # Anyone can register
    serializer_class = RegisterSerializer

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

# Project ViewSet
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Document ViewSet
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(project__user=self.request.user)

    def perform_create(self, serializer):
        from .document_processing import process_document
        document = serializer.save()
        # Trigger the Celery task asynchronously
        print('processing',document.id)
        doc = Document.objects.get(id=document.id)
        process_document(doc)
        # process_document_task.delay(document.id)

# Question ViewSet
class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Question.objects.filter(project__user=self.request.user)

    @action(detail=True, methods=['get'])
    def get_answer(self, request, pk=None):
        question = self.get_object()
        try:
            answer_text = answer_question(question)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        serializer = AnswerSerializer({'answer': answer_text})
        return Response(serializer.data)
