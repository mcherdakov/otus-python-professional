from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.views import redirect_to_login

from .forms import SignUpForm, SettingsForm
from .models import User


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'users/signup.html'


class ProfileView(UpdateView):
    model = User
    form_class = SettingsForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('index')

    def user_passes_test(self, request):
        if request.user.is_authenticated:
            return self.get_object() == request.user
        return False

    def dispatch(self, request, *args, **kwargs):
        if not self.user_passes_test(request):
            return redirect_to_login(request.get_full_path())
        return super(ProfileView, self).dispatch(request, *args, **kwargs)
