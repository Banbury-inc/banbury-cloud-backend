from django import forms

class UserForm(forms.Form):
    username = forms.CharField(label='Enter your username', max_length=100)
