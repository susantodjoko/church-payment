from django import forms
from .models import Keluarga, Member, Lingkungan


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'member_id', 'full_name', 'gender', 'date_of_birth',
            'address', 'phone', 'join_date', 'lingkungan', 'keluarga', 'is_active',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'join_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['lingkungan'].queryset = Lingkungan.objects.select_related('wilayah')
        self.fields['lingkungan'].widget.attrs.update({
            'hx-get': '/members/keluarga-options/',
            'hx-target': '#keluarga-select-wrap',
            'hx-trigger': 'change',
        })
        self.fields['keluarga'].required = False
        self.fields['keluarga'].label = 'Keluarga (KK)'
        # Scope dropdown to the current instance's lingkungan if editing
        instance = kwargs.get('instance')
        if instance and instance.lingkungan_id:
            self.fields['keluarga'].queryset = Keluarga.objects.filter(
                lingkungan_id=instance.lingkungan_id, is_active=True
            )
        else:
            self.fields['keluarga'].queryset = Keluarga.objects.none()
