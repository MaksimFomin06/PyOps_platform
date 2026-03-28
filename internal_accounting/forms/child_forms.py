from django import forms
from internal_accounting.models import Child, ChildRefund


class ChildStudentForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = '__all__'
        exclude = ['sequence_number', 'statement_year']
        widgets = {
            'date_of_buyback': forms.DateInput(attrs={'type': 'date'}),
            'first_visit_date': forms.DateInput(attrs={'type': 'date'}),
            'comment_for_payback': forms.Textarea(attrs={'rows': 3}),
        }


class ChildRefundForm(forms.ModelForm):
    class Meta:
        model = ChildRefund
        fields = ['student', 'summ_of_refund', 'date_of_refund', 'comment_for_refund']
        widgets = {
            'date_of_refund': forms.DateInput(attrs={'type': 'date'}),
            'comment_for_refund': forms.Textarea(attrs={'rows': 3}),
        }