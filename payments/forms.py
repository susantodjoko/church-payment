from django import forms
from django.core.validators import MinValueValidator
from django.db.models import Case, When, IntegerField, Value
from django.utils import timezone
from .models import Payment, PaymentType

PKSS_TYPE_NAME = 'Iuran PKSS'
KARTU_KUNING_TYPE_NAME = 'Iuran Kartu Kuning'


class PaymentForm(forms.ModelForm):
    member_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    member_display = forms.CharField(
        label='Anggota',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ketik nama anggota...',
            'autocomplete': 'off',
            'hx-get': '/members/search/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#member-search-results',
            'hx-indicator': '#member-search-spinner',
            'name': 'q',
        })
    )
    keluarga_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    keluarga_display = forms.CharField(
        label='Keluarga (KK)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ketik nomor atau nama KK...',
            'autocomplete': 'off',
            'hx-get': '/members/keluarga/search/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#keluarga-search-results',
            'hx-indicator': '#keluarga-search-spinner',
            'name': 'q',
        })
    )

    class Meta:
        model = Payment
        fields = ['payment_type', 'amount', 'date_received', 'period_month', 'period_year', 'notes']
        widgets = {
            'date_received': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_type'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000'}),
            'period_month': forms.Select(choices=[(i, i) for i in range(1, 13)], attrs={'class': 'form-select'}),
            'period_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Opsional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_type'].empty_label = None
        self.fields['payment_type'].queryset = PaymentType.objects.filter(is_active=True).order_by(
            Case(When(name=PKSS_TYPE_NAME, then=Value(0)), default=Value(1), output_field=IntegerField()),
            'name',
        )
        now = timezone.localtime(timezone.now())
        self.fields['date_received'].initial = now.strftime('%Y-%m-%dT%H:%M')
        self.fields['period_month'].initial = now.month
        self.fields['period_year'].initial = now.year
        self.fields['notes'].required = False
        self.fields['amount'].validators.append(MinValueValidator(1))
