from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from profdetails.models import Equipment, WorkingConditions, JobDetails

class QuantityFilter(admin.SimpleListFilter):
    title = 'Дежурные'  # Название фильтра в интерфейсе
    parameter_name = 'quantity'  # Параметр URL, который будет использоваться для фильтрации

    def lookups(self, request, model_admin):
        return [
            ('дежурные', 'Дежурные'),  # Значение (параметр URL, отображаемое название)
        ]

    def queryset(self, request, queryset):
        if self.value() == 'дежурные':
            return queryset.filter(quantity__iexact="Дежурные")
        else:
            return queryset


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']
    list_filter = ['siz', QuantityFilter]

@admin.register(WorkingConditions)
class WorkingConditionsAdmin(admin.ModelAdmin):
    pass

@admin.register(JobDetails)
class JobDetailsAdmin(SimpleHistoryAdmin):
    search_fields = ['profession']
    list_filter = ['department','working_conditions']
    list_select_related = ['profession','department']
    ordering = ['date_of_sout', 'department']
    actions = ['copy_job_details']

    @admin.action(description='Копировать похожие рабочие места')
    def copy_job_details(self, request, queryset):
        for obj in queryset:
            new_obj = JobDetails(
                profession=obj.profession,
                department=obj.department,
                working_conditions=obj.working_conditions,
                date_of_sout=obj.date_of_sout,
                opr=obj.opr
            )
            new_obj.save()

        message_bit = f"Скопировано {queryset.count()} рабочих мест"
        self.message_user(request, message_bit)




