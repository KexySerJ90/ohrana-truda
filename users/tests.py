from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from http import HTTPStatus

from main.models import Departments
import uuid
from random import randint



class RegisterUserTestCase(TestCase):
    def setUp(self):
        dep=Departments.objects.create(id=8,name='Отд 8')
        unique_suffix = str(uuid.uuid4()).replace("-", "")[:5]  # Take 5 characters from a UUID
        self.username=f'user_{unique_suffix}'
        self.email=f'user_{unique_suffix}@mail.ru'
        self.phone= f'+79999999{randint(100, 999)}'
        self.first_name='Sergey'
        self.last_name='User'
        self.cat2=dep.id,
        self.status= 'medic'
        self.date_of_work= '2024-11-04'
        self.password1= '12345678Aa'
        self.password2= '12345678Aa'


    def test_form_registration_get(self):
        path = reverse('users:register')
        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'users/register.html')

    def test_user_registration_success(self):
        data = {
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'cat2': self.cat2,
            'status': self.status,
            'date_of_work': self.date_of_work,
            'password1': self.password1,
            'password2': self.password2,
        }
        user_model = get_user_model()
        path = reverse('users:register')
        response = self.client.post(path, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(user_model.objects.filter(username=data['username']).exists())