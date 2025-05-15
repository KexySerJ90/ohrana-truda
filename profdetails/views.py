import base64
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, FormView
from ohr.settings import API_URL_KANDINSKY, env
from profdetails.forms import ProfessionForm
from profdetails.models import JobDetails
from profdetails.utils import Text2ImageAPI
from users.models import Profession
from typing import Optional, Dict, Any


class SIZForm(LoginRequiredMixin, FormView):
    """Представление для отображения формы СИЗ"""
    template_name = 'profdetails/siz_form.html'
    form_class = ProfessionForm
    extra_context = {'title': "Калькулятор СИЗ"}


class EquipmentListView(LoginRequiredMixin, View):
    """Представление для получения результата СИЗ по профессии"""
    def get(self, request) -> JsonResponse:
        profession_id = request.GET.get('profession_id')
        equipment_list = []

        if profession_id:
            profession = Profession.objects.get(id=profession_id)
            equipment_queryset = profession.equipment.all()

            for equipment in equipment_queryset:
                equipment_list.append({
                    'description': equipment.description,
                    'quantity': equipment.quantity,
                    'basis': equipment.basis,
                })

        return JsonResponse({'equipment': equipment_list})


class SOUTUserView(LoginRequiredMixin, DetailView):
    """Представление для просмотра СОУТ"""
    template_name = 'profdetails/sout.html'
    model = JobDetails
    extra_context = {'title': "Результаты специальной оценки условий труда"}
    context_object_name = 'workplace'

    def get_object(self, queryset: Optional[JobDetails] = None) -> Optional[JobDetails]:
        user = self.request.user
        try:
            # Получаем рабочее место по профессии и отделению текущего пользователя
            obj = JobDetails.objects.get(
                profession=user.profile.profession,
                department=user.cat2
            )
        except JobDetails.DoesNotExist:
            obj = None
        return obj


class GenerateImageView(View):
    """Представление для генерации изображения"""
    template_name: str = 'profdetails/generate_image_form.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        prompt: Optional[str] = request.session.get('prompt')
        return render(request, self.template_name, {'prompt': prompt})

    def post(self, request: HttpRequest) -> HttpResponse:
        prompt: Optional[str] = request.POST.get('prompt')
        style: Optional[str] = request.POST.get('style')
        api_url: str = API_URL_KANDINSKY
        api_key: str = env('API_KEY_KANDINSKY')
        secret_key: str = env('API_SECRET_KANDINSKY')

        api = Text2ImageAPI(api_url, api_key, secret_key)
        pipeline_id = api.get_pipeline()
        uuid: str = api.generate(prompt, pipeline_id, style=style)
        files : Optional[list] = api.check_generation(uuid)

        if files :
            image_data: str = files[0]
            context: Dict[str, Any] = {'image_data': image_data}
            request.session['prompt'] = prompt
            return render(request, 'profdetails/preview_image.html', context)

        return render(request, self.template_name, {'error': 'Изображение не было сгенерировано.'})


class SaveImageView(View):
    """Представление для сохранения сгенеиророванного изображения на аватар пользователя"""
    def post(self, request: HttpRequest) -> HttpResponse:
        prompt: Optional[str] = request.session.get('prompt')
        image_data: Optional[str] = request.POST.get('image_data')
        ext: str = 'png'

        if prompt and image_data:
            filename: str = f'{prompt}.{ext}'
            # Декодируем изображение
            decoded_img: bytes = base64.b64decode(image_data)
            # Сохраняем файл
            request.user.profile.photo.save(filename, ContentFile(decoded_img), save=True)
            del self.request.session['prompt']

        return redirect('users:profile')
