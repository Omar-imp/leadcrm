from django import forms
from .models import Lead, FollowUp


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            'lead_source', 'name', 'contact_number', 'email',
            'country', 'city', 'address', 'quotation', 'detail',
        ]
        widgets = {
            'lead_source': forms.RadioSelect(),
            'name': forms.TextInput(attrs={'placeholder': 'Enter Name', 'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'placeholder': 'Enter Contact Number', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter Email', 'class': 'form-control'}),
            'country': forms.TextInput(attrs={'placeholder': 'Select Country', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'placeholder': 'Select City', 'class': 'form-control'}),
            'address': forms.TextInput(attrs={'placeholder': 'Enter Address', 'class': 'form-control'}),
            'quotation': forms.NumberInput(attrs={'class': 'form-control'}),
            'detail': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['follow_up_date', 'notes']
        widgets = {
            'follow_up_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }