def subject_completions(request):
    if request.user.is_authenticated:
        return {
            'subject_completions': request.user.subject_completions.all()
        }
    return {}


