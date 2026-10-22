from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from .models import Review, Enquiry, UserProfile


class CustomerRegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Full Name'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            from allauth.socialaccount.models import SocialAccount
            if SocialAccount.objects.filter(user__email__iexact=email, provider='google').exists():
                raise forms.ValidationError("This email is already registered via Google. Please use \"Continue with Google\" to sign in instead.")
            raise forms.ValidationError("An account with this email already exists. Please sign in instead.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['reviewer_name', 'rating', 'title', 'body', 'photo']
        widgets = {
            'reviewer_name': forms.TextInput(attrs={'placeholder': 'Your name'}),
            'rating': forms.RadioSelect(choices=[(i, f'{i}★') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={'placeholder': 'Review title'}),
            'body': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your experience...'}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'size') and photo.size > 8 * 1024 * 1024:
            raise forms.ValidationError('Photo is too large (max 8 MB).')
        return photo


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ['full_name', 'phone', 'email', 'subject', 'message', 'image']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email Address'}),
            'subject': forms.TextInput(attrs={'placeholder': 'What can we help you with?'}),
            'message': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Your message...'}),
        }


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=20)
    alternate_phone = forms.CharField(max_length=20, required=False)
    email = forms.EmailField()
    address_line1 = forms.CharField(max_length=250, required=False)   # Flat / House no. / Building
    address_line2 = forms.CharField(max_length=250, required=False)   # Area / Street / Village
    landmark = forms.CharField(max_length=200, required=False)
    # Legacy single-box address (older clients/tests) — used when address_line1 is not sent.
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    city = forms.CharField(max_length=100)
    state = forms.CharField(max_length=100)
    pincode = forms.CharField(max_length=10)

    def clean(self):
        data = super().clean()
        line1 = (data.get('address_line1') or '').strip()
        line2 = (data.get('address_line2') or '').strip()
        landmark = (data.get('landmark') or '').strip()
        if not line1:
            legacy = (data.get('address') or '').strip()
            if not legacy:
                self.add_error('address_line1', 'Please enter your flat / house no. / building.')
                return data
            line1 = legacy
        parts = [line1]
        if line2:
            parts.append(line2)
        if landmark:
            parts.append('Near ' + landmark)
        data['address_line1'], data['address_line2'], data['landmark'] = line1, line2, landmark
        data['address'] = ', '.join(parts)
        return data


class CustomSocialSignupForm(SocialSignupForm):
    """
    Shown once, only to brand-new Google sign-ups (existing accounts with a
    matching email are auto-connected and never see this). Lets them confirm
    their name and requires Terms & Conditions agreement before the account
    is actually created — keeping Google sign-up consistent with the site's
    own registration flow instead of skipping the terms step entirely.
    """
    full_name = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'placeholder': 'Your full name', 'class': 'form-input'}))
    agree_terms = forms.BooleanField(required=True, error_messages={'required': 'Please agree to the Terms & Conditions to create an account.'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_name = (self.sociallogin.user.get_full_name() or '').strip()
        if initial_name:
            self.fields['full_name'].initial = initial_name
        # Email comes from Google and shouldn't be hand-edited here.
        if 'email' in self.fields:
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['class'] = 'form-input'
            self.fields['email'].widget.attrs['style'] = 'background:#f0f0f0;color:var(--text-muted);cursor:not-allowed;'

    def save(self, request):
        user = super().save(request)
        full_name = (self.cleaned_data.get('full_name') or '').strip()
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.save(update_fields=['first_name', 'last_name'])
        return user
