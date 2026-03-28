from django import forms
from .models import SessionLog


class SessionLogForm(forms.ModelForm):
    student_search = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ФИО или номер ведомости',
            'autocomplete': 'off',
            'id': 'student-search-input'
        }),
        label="Поиск студента *"
    )
    
    selected_student_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'selected-student-id'})
    )
    selected_child_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'selected-child-id'})
    )
    
    hour_times_display = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '13:00, 14:00, 15:00',
            'id': 'hour-times-display',
            'readonly': 'readonly'
        }),
        label="Время занятий"
    )
    
    class Meta:
        model = SessionLog
        fields = [
            'student_type',
            'instructor',
            'session_date',
            'hours_count',
            'hour_times',
            'comment',
        ]
        widgets = {
            'student_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'student-type-select'
            }),
            'instructor': forms.Select(attrs={'class': 'form-control'}),
            'session_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'hours_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
                'id': 'hours-count-input',
            }),
            'hour_times': forms.HiddenInput(attrs={'id': 'hour-times-hidden'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def clean_hours_count(self):
        hours = self.cleaned_data.get('hours_count', 1)
        if hours < 1 or hours > 10:
            raise forms.ValidationError('Количество часов должно быть от 1 до 10')
        return hours
    
    def clean(self):
        cleaned_data = super().clean()
        student_type = cleaned_data.get('student_type')
        selected_student_id = cleaned_data.get('selected_student_id')
        selected_child_id = cleaned_data.get('selected_child_id')
        
        if student_type == 'adult' and not selected_student_id:
            raise forms.ValidationError('Выберите студента из списка')
        elif student_type == 'child' and not selected_child_id:
            raise forms.ValidationError('Выберите студента из списка')
        
        return cleaned_data