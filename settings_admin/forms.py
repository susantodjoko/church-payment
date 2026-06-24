from django import forms
from django.contrib.auth.models import User, Group
from members.models import Wilayah, Lingkungan, Keluarga
from payments.models import PaymentType


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=[('Super Admin', 'Super Admin'), ('Treasurer', 'Treasurer')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=self.cleaned_data['role'])
            user.groups.set([group])
        return user


class WilayahForm(forms.ModelForm):
    class Meta:
        model = Wilayah
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'})}


class LingkunganForm(forms.ModelForm):
    class Meta:
        model = Lingkungan
        fields = ['name', 'wilayah']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'wilayah': forms.Select(attrs={'class': 'form-select'}),
        }


class PaymentTypeForm(forms.ModelForm):
    class Meta:
        model = PaymentType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class KeluargaForm(forms.ModelForm):
    class Meta:
        model = Keluarga
        fields = ['kk_number', 'name', 'lingkungan', 'is_active']
        widgets = {
            'kk_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'lingkungan': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
