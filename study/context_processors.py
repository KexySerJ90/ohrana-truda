def subject_completions(request):
    if request.user.is_authenticated:
        return {
            'subject_completions': request.user.subject_completions.all().select_related('subjects')
        }
    return {}


def achievements(request):
    if request.user.is_authenticated:
        achievements=request.user.achievements.filter(user=request.user, is_received=False)
        return {
            'achievements': achievements,
            'achievements_count':achievements.count()
        }
    return {}