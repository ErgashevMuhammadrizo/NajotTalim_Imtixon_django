"""
Users app forms - Custom forms for user management
ULTRA PRO MAX VERSIYA
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with validation"""
    
    password1 = forms.CharField(
        label=_('Parol'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Parol kiriting'),
            'autocomplete': 'new-password',
        }),
        help_text=_("""
            <small class="form-text text-muted">
                Parol kamida 8 ta belgidan iborat bo'lishi kerak.<br>
                Katta va kichik harflar, raqamlar va maxsus belgilar aralashmasi bo'lishi tavsiya etiladi.
            </small>
        """),
    )
    
    password2 = forms.CharField(
        label=_('Parolni tasdiqlash'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Parolni takrorlang'),
            'autocomplete': 'new-password',
        }),
    )
    
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@mail.com',
            'autocomplete': 'email',
        }),
        help_text=_('Iltimos, haqiqiy email manzil kiriting.'),
    )
    
    phone = forms.CharField(
        label=_('Telefon raqam'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998901234567',
            'autocomplete': 'tel',
        }),
        help_text=_('Format: +998901234567'),
        required=False,
    )
    
    terms = forms.BooleanField(
        label=_('Foydalanish shartlari'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True,
        }),
        error_messages={'required': _('Foydalanish shartlari bilan rozilik bildirishingiz kerak')},
    )
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Foydalanuvchi nomi'),
                'autocomplete': 'username',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Ism'),
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Familiya'),
                'autocomplete': 'family-name',
            }),
        }
        help_texts = {
            'username': _('150 ta belgidan kam. Faqat harflar, raqamlar va @/./+/-/_ belgilari.'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower().strip()
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError(_("Bu email allaqachon ro'yxatdan o'tgan"))
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username').strip()
        if not re.match(r'^[\w.@+-]+\Z', username):
            raise ValidationError(_("Faqat harflar, raqamlar va @/./+/-/_ belgilari ruxsat etilgan"))
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError(_("Bu foydalanuvchi nomi allaqachon band"))
        return username
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = phone.strip()
            # Remove any non-digit characters except +
            phone = re.sub(r'[^\d+]', '', phone)
            
            # Check if starts with +998
            if not phone.startswith('+998'):
                if phone.startswith('998'):
                    phone = '+' + phone
                elif phone.startswith('0'):
                    phone = '+998' + phone[1:]
                else:
                    phone = '+998' + phone
            
            # Validate length
            if len(phone) != 13:  # +998901234567
                raise ValidationError(_("Telefon raqami 13 ta raqam bo'lishi kerak"))
            
            if CustomUser.objects.filter(phone=phone).exists():
                raise ValidationError(_("Bu telefon raqam allaqachon ro'yxatdan o'tgan"))
        
        return phone
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        validate_password(password1)
        return password1
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            self.add_error('password2', _("Parollar bir-biriga mos emas"))
        
        return cleaned_data


class LoginForm(forms.Form):
    """Login form with remember me option"""
    
    username = forms.CharField(
        label=_('Foydalanuvchi nomi yoki Email'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('username yoki email'),
            'autocomplete': 'username',
            'autofocus': True,
        }),
    )
    
    password = forms.CharField(
        label=_('Parol'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Parol'),
            'autocomplete': 'current-password',
        }),
    )
    
    remember_me = forms.BooleanField(
        label=_('Meni eslab qol'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['autofocus'] = True
    
    def clean_username(self):
        username = self.cleaned_data.get('username').strip()
        if not username:
            raise ValidationError(_("Foydalanuvchi nomi yoki email kiriting"))
        return username


class ProfileUpdateForm(forms.ModelForm):
    """Profile update form"""
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'date_of_birth', 'country', 'language',
            'default_currency', 'timezone', 'bio'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Ism'),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Familiya'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@mail.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+998901234567',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'country': forms.Select(attrs={
                'class': 'form-control',
            }),
            'language': forms.Select(attrs={
                'class': 'form-control',
            }),
            'default_currency': forms.Select(attrs={
                'class': 'form-control',
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-control',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Ozingiz haqingizda qisqacha...'),
                'maxlength': '500',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email read-only for security
        self.fields['email'].widget.attrs['readonly'] = True
    
    def clean_email(self):
        # Don't allow email change through profile update
        return self.instance.email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = phone.strip()
            # Remove any non-digit characters except +
            phone = re.sub(r'[^\d+]', '', phone)
            
            # Check if starts with +998
            if not phone.startswith('+998'):
                if phone.startswith('998'):
                    phone = '+' + phone
                elif phone.startswith('0'):
                    phone = '+998' + phone[1:]
                else:
                    phone = '+998' + phone
            
            # Validate length
            if len(phone) != 13:  # +998901234567
                raise ValidationError(_("Telefon raqami 13 ta raqam bo'lishi kerak"))
            
            # Check if phone is already used by another user
            if CustomUser.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
                raise ValidationError(_("Bu telefon raqam allaqachon band qilingan"))
        
        return phone


class PasswordResetForm(forms.Form):
    """Password reset request form"""
    
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@mail.com',
            'autocomplete': 'email',
        }),
        help_text=_('Roʻyxatdan oʻtgan email manzilingizni kiriting.'),
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower().strip()
        return email


class PasswordResetConfirmForm(forms.Form):
    """Password reset confirmation form"""
    
    new_password1 = forms.CharField(
        label=_('Yangi parol'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Yangi parol'),
            'autocomplete': 'new-password',
        }),
        help_text=_("""
            <small class="form-text text-muted">
                Parol kamida 8 ta belgidan iborat bo'lishi kerak.<br>
                Katta va kichik harflar, raqamlar va maxsus belgilar aralashmasi bo'lishi tavsiya etiladi.
            </small>
        """),
    )
    
    new_password2 = forms.CharField(
        label=_('Yangi parolni tasdiqlash'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Parolni takrorlang'),
            'autocomplete': 'new-password',
        }),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['autofocus'] = True
    
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        validate_password(password1)
        return password1
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            self.add_error('new_password2', _("Parollar bir-biriga mos emas"))
        
        return cleaned_data


class ProfileImageForm(forms.ModelForm):
    """Profile image upload form"""
    
    class Meta:
        model = CustomUser
        fields = ['profile_image']
        widgets = {
            'profile_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            })
        }
    
    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError(_('Rasm hajmi 5MB dan oshmasligi kerak'))
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            extension = image.name.split('.')[-1].lower()
            if f'.{extension}' not in valid_extensions:
                raise ValidationError(_('Faqat JPG, PNG, GIF yoki WebP formatidagi rasmlar qabul qilinadi'))
        
        return image


class NotificationSettingsForm(forms.ModelForm):
    """Notification settings form"""
    
    class Meta:
        model = CustomUser
        fields = ['email_notifications', 'push_notifications', 'marketing_emails']
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'push_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'marketing_emails': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'email_notifications': _('Email xabarnomalarni olish'),
            'push_notifications': _('Push xabarnomalarni olish'),
            'marketing_emails': _('Marketing email larini olish'),
        }


class AccountDeletionForm(forms.Form):
    """Account deletion confirmation form"""
    
    confirm_text = forms.CharField(
        label=_('Tasdiqlash'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('"DELETE" yozing'),
        }),
        help_text=_('Hisobni o\'chirishni tasdiqlash uchun "DELETE" so\'zini yozing.'),
    )
    
    def clean_confirm_text(self):
        confirm_text = self.cleaned_data.get('confirm_text').strip()
        if confirm_text != 'DELETE':
            raise ValidationError(_('"DELETE" so\'zini to\'g\'ri yozing'))
        return confirm_text