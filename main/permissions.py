
class AuthorPermissionsMixin:
    def has_permissions(self):
        if self.user_has_category_permission() or self.request.user.is_superuser or self.is_special_category():
            return True
        return False

    def user_has_category_permission(self):
        return self.request.user.cat2.slug == self.kwargs['dep_slug']

    def is_special_category(self):
        special_categories = ['administraciya', 'sout', 'obshie', 'shablony']
        return self.kwargs['dep_slug'] in special_categories



