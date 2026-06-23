from django import forms
from .models import Lead, FollowUp
from .models import Lead, FollowUp, Payment, ScheduledPayment, Installment


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

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_type', 'amount', 'notes']
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional note'}),
        }


class ScheduledPaymentForm(forms.ModelForm):
    class Meta:
        model = ScheduledPayment
        fields = ['lead', 'total_amount', 'notes']
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-control'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InstallmentForm(forms.ModelForm):
    class Meta:
        model = Installment
        fields = ['amount', 'due_date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional note'}),
        }