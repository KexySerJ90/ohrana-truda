from django.db import models
from simple_history.models import HistoricalRecords

from users.models import Profession


class Equipment(models.Model):
    name = models.CharField(max_length=350,verbose_name='Название средств индивидуальной защиты', unique=True, db_index=True)
    description=models.CharField(max_length=500,verbose_name='Описание СИЗ')
    quantity = models.CharField(default='1', verbose_name='Количество')
    basis=models.CharField(max_length=500, verbose_name='Основание', null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "СИЗ"
        verbose_name_plural = "СИЗ"

class WorkingConditions(models.Model):
    name = models.CharField(max_length=250, verbose_name='Класс условий труда', unique=True, db_index=True)
    description=models.CharField(max_length=250, verbose_name='Описание', blank=True, null=True)
    money=models.PositiveIntegerField(verbose_name='Повышенная оплата труда,%',blank=True, null=True)
    weekend=models.PositiveIntegerField(verbose_name='Дополнительный отпуск,количество дней',blank=True, null=True)
    duration = models.BooleanField(verbose_name='Сокращенная продолжительность рабочего времени, да/нет')
    milk = models.BooleanField(verbose_name='Молоко, да/нет')
    food=models.BooleanField(verbose_name='Лечебно-профилактическое питание, да/нет')
    pension=models.BooleanField(verbose_name='Льготное пенсионное обеспечение, да/нет')
    medical = models.BooleanField(verbose_name='Проведение медицинских осмотров, да/нет')

    class Meta:
        verbose_name = 'Условия труда'
        verbose_name_plural = 'Условия труда'

    def __str__(self):
        return self.name

class JobDetails(models.Model):
    class OPR(models.TextChoices):
        LOW=('low', 'Низкий')
        MODERATE=('moderate', 'Умеренный')
        MEDIUM=('medium', 'Средний')
        SIGNIFICANT = ('significant', 'Значительный')
        HIGH = ('high', 'Высокий')
    profession = models.ForeignKey(Profession, on_delete=models.CASCADE, verbose_name='Должность')
    department = models.ForeignKey('users.Departments', on_delete=models.CASCADE, verbose_name='Отделение')
    working_conditions = models.ForeignKey(WorkingConditions, on_delete=models.CASCADE, verbose_name='Условия труда', null=True, blank=True)
    date_of_sout=models.DateField(verbose_name='Дата СОУТ',blank=True,null=True)
    opr = models.CharField(choices=OPR.choices, max_length=100, verbose_name='Уровень риска', blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('profession', 'department')
        verbose_name = 'Рабочее место'
        verbose_name_plural = 'Рабочие места'

    def __str__(self):
        return f'{self.department}-{self.profession}'


