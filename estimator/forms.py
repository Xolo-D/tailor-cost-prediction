from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import TailorProfile


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email', 'autocomplete': 'email'}),
        label='Email'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs.update({'placeholder': 'Enter your password'})

    class Meta:
        model = User
        fields = ['username', 'password']


class RegisterForm(UserCreationForm):
    email      = forms.EmailField(required=True,
                    widget=forms.EmailInput(attrs={'placeholder': 'Email address'}))
    first_name = forms.CharField(max_length=50, required=True,
                    widget=forms.TextInput(attrs={'placeholder': 'First name'}))
    last_name  = forms.CharField(max_length=50, required=True,
                    widget=forms.TextInput(attrs={'placeholder': 'Last name'}))

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email    = self.cleaned_data['email']
        user.username = self.cleaned_data['email']   # use email as username
        if commit:
            user.save()
            TailorProfile.objects.create(user=user)
        return user


class ProfileForm(forms.ModelForm):
    first_name  = forms.CharField(max_length=50)
    last_name   = forms.CharField(max_length=50)
    institution = forms.CharField(max_length=200)
    bio         = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    class Meta:
        model  = TailorProfile
        fields = ['institution', 'bio']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.user:
            self.fields['first_name'].initial = instance.user.first_name
            self.fields['last_name'].initial  = instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data['first_name']
        profile.user.last_name  = self.cleaned_data['last_name']
        if commit:
            profile.user.save()
            profile.save()
        return profile


class EstimateForm(forms.Form):
    GARMENT_CHOICES = [('', 'Select type')] + [
        (g, g) for g in [
            'Blouse', 'Coat', 'Dress', 'Hoodie', 'Jacket',
            'Jersey', 'Shirt', 'Shorts', 'Skirt', 'Suit', 'Tracksuit', 'Trousers',
        ]
    ]
    FABRIC_CHOICES = [('', 'Select fabric type...')] + [
        (f, f) for f in ['Cotton', 'Denim', 'Leather', 'Linen', 'Nylon', 'Polyester', 'Silk', 'Wool']
    ]

    garment     = forms.ChoiceField(choices=GARMENT_CHOICES, label='Garment Type')
    fabric_type = forms.ChoiceField(choices=FABRIC_CHOICES, label='Fabric Type')
    fabric_m    = forms.FloatField(
        min_value=0.1, max_value=20,
        label='Fabric Meters',
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 2.5', 'step': '0.1'})
    )
