from django import forms

class EmissionsUploadForm(forms.Form):
    organization = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    file = forms.FileField(help_text="CSV with columns: date,value,scope,activity")
