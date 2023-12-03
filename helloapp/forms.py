from django import forms

class UserForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
