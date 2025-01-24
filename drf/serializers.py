from django.contrib.auth import get_user_model
from rest_framework import serializers
from main.models import Article, UploadFiles, JobDetails
from study.models import SubjectCompletion
from users.models import UserLoginHistory


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('id', 'title', 'content', 'is_published', 'category')


class UploadFilesSerializer(serializers.ModelSerializer):
    cat_name = serializers.CharField(source='cat.name', read_only=True)

    class Meta:
        model = UploadFiles
        fields = ('id', 'cat_name', 'file', 'title', 'uploaded_at')


class SubjectCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectCompletion
        fields = ('subjects', 'completed', 'score', 'study_completed')


class LeaderSerializer(serializers.ModelSerializer):
    cat_name = serializers.CharField(source='cat2.name', read_only=True)
    subject_completions = SubjectCompletionSerializer(many=True, read_only=True)
    instructaj = serializers.CharField(source='user.profile.instructaj', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'status', 'cat_name', 'instructaj', 'last_activity', 'subject_completions')


class ProfileUserSerializer(serializers.ModelSerializer):
    cat_name = serializers.CharField(source='cat2.name', read_only=True)
    photo = serializers.ImageField(source='profile.photo')
    patronymic = serializers.CharField(source='profile.patronymic')
    prof = serializers.CharField(source='profile.profession')
    date_birth = serializers.DateField(source='profile.date_birth')

    class Meta:
        model = get_user_model()
        fields = (
        'id', 'photo', 'username', 'first_name', 'last_name', 'patronymic', 'cat_name', 'status', 'prof', 'date_birth')
        read_only_fields = ('id', 'username', 'cat_name', 'status')


class UserLoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLoginHistory
        fields = ('id', 'login_time', 'ip_address', 'location', 'device_type', 'browser', 'os')


class JobDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDetails
        fields = '__all__'
