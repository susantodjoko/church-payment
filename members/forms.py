from django import forms
from .models import Member, Lingkungan


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'member_id', 'full_name', 'gender', 'date_of_birth',
            'address', 'phone', 'join_date', 'lingkungan', 'is_active',
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
