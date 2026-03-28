from django import forms
from internal_accounting.models import AdultStudent, AdultRefund


class AdultStudentForm(forms.ModelForm):
    class Meta:
        model = AdultStudent
        fields = '__all__'
        exclude = ['sequence_number', 'statement_year']
        widgets = {
            'date_of_buyback': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_visit_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'comment_for_payback': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'transferred_the_certificate': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
    
    fio = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        return ''.join(filter(str.isdigit, phone)) or phone
    
    def clean_summ_of_payback(self):
        amount = self.cleaned_data.get('summ_of_payback')
        if amount and amount <= 0:
            raise forms.ValidationError('Сумма платежа должна быть больше 0')
        return amount


class AdultRefundForm(forms.ModelForm):
    class Meta:
        model = AdultRefund
        fields = ['student', 'summ_of_refund', 'date_of_refund', 'comment_for_refund']
        widgets = {
            'date_of_refund': forms.DateInput(attrs={'type': 'date'}),
            'comment_for_refund': forms.Textarea(attrs={'rows': 3}),
        }