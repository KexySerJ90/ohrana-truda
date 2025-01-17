from django.contrib.auth import get_user_model
from rest_framework import generics, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf.permissions import IsAdminOrReadOnly
from drf.serializers import ArticleSerializer, UploadFilesSerializer, LeaderSerializer, ProfileUserSerializer, \
    UserLoginHistorySerializer, JobDetailsSerializer
from main.models import Article, Categorys, UploadFiles, Departments
from users.models import UserLoginHistory, JobDetails, WorkingConditions

from users.utils import UserQuerysetMixin


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = (IsAdminOrReadOnly, )

    @action(methods=['get'], detail=False)
    def category(self, request):
        cats=Categorys.objects.all()
        return Response({'cats': [c.name for c in cats]})

    @action(methods=['get'], detail=True)
    def categorys(self, request, pk=None):
        cats=Categorys.objects.get(pk=pk)
        return Response({'cats': cats.name})

# class ArticleApiView(generics.ListCreateAPIView):
#     queryset = Article.objects.all()
#     serializer_class = ArticleSerializer
#
#
# class ArticleApiUpdate(generics.UpdateAPIView):
#     queryset = Article.objects.all()
#     serializer_class = ArticleSerializer

class UploadFilesViewSet(viewsets.ModelViewSet):
    serializer_class = UploadFilesSerializer
    permission_classes = (IsAdminOrReadOnly, )

    def get_queryset(self):
        user = self.request.user
        # Получаем ID отделений пользователя
        user_department_ids = user.cat2.id if user.cat2 else []

        # Фильтруем по ID отделений, которые разрешены, и ID отделений пользователя
        return UploadFiles.objects.filter(
            cat__id__in=[6, 1, 2] + [user_department_ids]
        ).select_related('cat')


class LeaderViewSet(viewsets.ViewSet, UserQuerysetMixin):
    serializer_class = LeaderSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        queryset = self.get_user_queryset(user)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)


class ProfileAPIUpdate(mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    serializer_class = ProfileUserSerializer
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        user = self.request.user
        return get_user_model().objects.filter(pk=user.id)


class UserLoginHistoryViewSet(mixins.RetrieveModelMixin,mixins.ListModelMixin,viewsets.GenericViewSet):
    serializer_class = UserLoginHistorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return UserLoginHistory.objects.filter(user=user)


class JobDetailsListViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin,viewsets.GenericViewSet):
    serializer_class = JobDetailsSerializer
    permission_classes = [IsAuthenticated]
    queryset = JobDetails.objects.all()

    @action(methods=['get'], detail=False)
    def working_conditions(self, request, pk=None):
        working_conditions = WorkingConditions.objects.all()
        return Response({'working_conditions': [c.name for c in working_conditions]})

    @action(methods=['get'], detail=True)
    def working_condition(self, request, pk=None):
        working_conditions = WorkingConditions.objects.get(pk=pk)
        return Response({'working_conditions': working_conditions.name})