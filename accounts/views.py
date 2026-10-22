from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .models import User, Role
from .forms import LoginForm, CreatorSignupForm, BrandSignupForm
from creator.models import CreatorProfile
from brands.models import BrandProfile
from audit.services import log_audit_event

def login_hub_view(request):
    if request.user.is_authenticated:
        if request.user.is_creator:
            return redirect('creator_dashboard')
        elif request.user.is_brand:
            return redirect('brand_dashboard')
        elif request.user.is_platform_admin:
            return redirect('admin_platform_dashboard')
    return render(request, 'accounts/login_hub.html')

def creator_login_view(request):
    if request.user.is_authenticated and request.user.is_creator:
        return redirect('creator_dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if not user:
                # Try finding by email
                u = User.objects.filter(email=username).first()
                if u:
                    user = authenticate(request, username=u.username, password=password)
            
            if user:
                if not user.is_active:
                    messages.error(request, 'Your account has been suspended or banned. Please contact platform support.')
                    return render(request, 'accounts/creator_login.html', {'form': form})
                if not user.is_creator:
                    messages.error(request, 'This login is for Creators. Brand users should log in at /brand/login/.')
                    return render(request, 'accounts/creator_login.html', {'form': form})
                
                login(request, user)
                log_audit_event(actor=user, action='CREATOR_LOGIN_SUCCESS', request=request)
                messages.success(request, f"Welcome back, @{user.username}!")
                return redirect('creator_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
                log_audit_event(action='CREATOR_LOGIN_FAILED', details={'username_attempt': username}, request=request)
    else:
        form = LoginForm()
    
    return render(request, 'accounts/creator_login.html', {'form': form})

def creator_signup_view(request):
    if request.user.is_authenticated:
        return redirect('creator_dashboard')
    
    if request.method == 'POST':
        form = CreatorSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = Role.CREATOR
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            niche = form.cleaned_data.get('niche', 'Lifestyle')
            CreatorProfile.objects.create(
                user=user,
                niche=niche,
                instagram_handle=user.username
            )
            
            login(request, user)
            log_audit_event(actor=user, action='CREATOR_SIGNUP_SUCCESS', request=request)
            messages.success(request, f"Account created! Welcome to MonkHQ, @{user.username}.")
            return redirect('creator_dashboard')
    else:
        form = CreatorSignupForm()
    
    return render(request, 'accounts/creator_signup.html', {'form': form})

def brand_login_view(request):
    if request.user.is_authenticated and request.user.is_brand:
        return redirect('brand_dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if not user:
                u = User.objects.filter(email=username).first()
                if u:
                    user = authenticate(request, username=u.username, password=password)
            
            if user:
                if not user.is_active:
                    messages.error(request, 'Your account has been suspended or banned. Please contact platform admin.')
                    return render(request, 'accounts/brand_login.html', {'form': form})
                if not user.is_brand:
                    messages.error(request, 'This login is for Brands. Creators should log in at /creator/login/.')
                    return render(request, 'accounts/brand_login.html', {'form': form})
                
                login(request, user)
                log_audit_event(actor=user, action='BRAND_LOGIN_SUCCESS', request=request)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('brand_dashboard')
            else:
                messages.error(request, 'Invalid brand credentials.')
                log_audit_event(action='BRAND_LOGIN_FAILED', details={'username_attempt': username}, request=request)
    else:
        form = LoginForm()
    
    return render(request, 'accounts/brand_login.html', {'form': form})

def brand_signup_view(request):
    if request.user.is_authenticated:
        return redirect('brand_dashboard')
    
    if request.method == 'POST':
        form = BrandSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = Role.BRAND
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            company_name = form.cleaned_data.get('company_name', user.username)
            industry = form.cleaned_data.get('industry', 'E-Commerce')
            BrandProfile.objects.create(
                user=user,
                company_name=company_name,
                industry=industry
            )
            
            login(request, user)
            log_audit_event(actor=user, action='BRAND_SIGNUP_SUCCESS', request=request)
            messages.success(request, f"Brand workspace created for {company_name}!")
            return redirect('brand_dashboard')
    else:
        form = BrandSignupForm()
    
    return render(request, 'accounts/brand_signup.html', {'form': form})

def admin_platform_login_view(request):
    if request.user.is_authenticated and request.user.is_platform_admin:
        return redirect('admin_platform_dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if not user:
                u = User.objects.filter(email=username).first()
                if u:
                    user = authenticate(request, username=u.username, password=password)
            
            if user:
                if not user.is_platform_admin:
                    messages.error(request, 'Access denied. You do not have Platform Admin privileges.')
                    return render(request, 'accounts/admin_login.html', {'form': form})
                
                login(request, user)
                log_audit_event(actor=user, action='ADMIN_LOGIN_SUCCESS', request=request)
                messages.success(request, "Logged into Platform Admin Control.")
                return redirect('admin_platform_dashboard')
            else:
                messages.error(request, 'Invalid admin credentials.')
                log_audit_event(action='ADMIN_LOGIN_FAILED', details={'username_attempt': username}, request=request)
    else:
        form = LoginForm()
    
    return render(request, 'accounts/admin_login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        log_audit_event(actor=request.user, action='LOGOUT', request=request)
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('creator_login')
