from django import forms
from django.utils import timezone
from .models import Payment, PaymentType


class PaymentForm(forms.ModelForm):
    member_id = forms.IntegerField(widget=forms.HiddenInput())
    member_display = forms.CharField(
        label='Anggota',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ketik nama anggota...',
            'autocomplete': 'off',
            'hx-get': '/members/search/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#search-results',
            'hx-vals': 'js:{q: event.target.value}',
        })
    )

    class Meta:
        model = Payment
        fields = ['payment_type', 'amount', 'date_paid', 'period_month', 'period_year', 'notes']
        widgets = {
            'date_paid': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000'}),
            'period_month': forms.Select(choices=[(i, i) for i in range(1, 13)], attrs={'class': 'form-select'}),
            'period_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_type'].queryset = PaymentType.objects.filter(is_active=True)
        now = timezone.localtime(timezone.now())
        self.fields['date_paid'].initial = now.strftime('%Y-%m-%dT%H:%M')
        self.fields['period_month'].initial = now.month
        self.fields['period_year'].initial = now.year
        self.fields['notes'].required = False
        self.fields['member_display'].required = False
        self.fields['member_id'].required = False
