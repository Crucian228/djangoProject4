from django.shortcuts import render, HttpResponse, redirect
from django.core.exceptions import ObjectDoesNotExist
from .forms import ChargeForm, CreateAccount, LoginForm, UserProfileForm
from .models import Account, Charge, User
from django.contrib.auth.models import Permission, ContentType

from .forms import ChargeForm, CreateAccount
from .models import Account, Charge
from .serializers import AccountSerializer, MonthStatCollection, UserSerializer, ChargeSerializer
from django.db.models import F
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import (login_required, permission_required)
from django.views.decorators.cache import never_cache, cache_control

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


# Enter to system
def login_view(request):
    user_form = LoginForm()
    if request.method == 'POST':
        user_form = LoginForm(request.POST)
        if user_form.is_valid():
            username = user_form.cleaned_data['username']
            password = user_form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if not user:
                info = 'The username and password were incorrect'
                return render(request, 'login.html', {'info': info})
            login(request, user)
            return redirect('profile_view', username=username)
    context = {'form': user_form}
    return render(request, 'login.html', context)


# Exit
def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return render(request, 'logout.html')


# Registration
@cache_control(no_cache=True)
def registration(request):
    user_form = UserProfileForm()
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST)
        if user_form.is_valid():
            username = user_form.cleaned_data['username']
            password = user_form.cleaned_data['password']
            phone_number = user_form.cleaned_data['phone_number']
            address = user_form.cleaned_data['address']
            user = User.objects.create_user(username=username,
                                            phone_number=phone_number,
                                            address=address)
            user.set_password(password)
            user.save()
            return redirect('user/(?P<username>\w+)', username)
        else:
            return HttpResponse('В имени пользователя использовать лишь буквы и цифры!')
    context = {'form': user_form}
    return render(request, 'registration.html', context)


# Profile view
@never_cache
@login_required(login_url='login')
def profile_view(request, username):
    profile = User.objects.get(username=username)
    if profile.is_authenticated:
        return render(request, 'profile.html', {'profile': profile})
    else:
        return HttpResponse("Something wrongs!")


@login_required(login_url='login')
@api_view(['GET'])
def serialized_profile_view(request, username):
    profile = User.objects.get(username=username)
    serializer = UserSerializer(profile)
    if profile.is_authenticated:
        return Response(serializer.data, status=status.HTTP_200_OK)


# Create the account
@login_required(login_url='login')
def create_account(request, username):
    user = User.objects.get(username=username)
    form = CreateAccount()
    if request.method == 'POST':
        form = CreateAccount(request.POST)
        if form.is_valid():
            with transaction.atomic():
                title = form.cleaned_data['title']
                account = Account(user=user, title=title, total=0)
                account.save()
            perm = Permission.objects.get(codename='can_view_profile')
            user.user_permissions.add(perm)
            return redirect('account_view', username, title)
        else:
            return HttpResponse("Not valid")
    context = {'form': form}
    return render(request, 'create_account.html', context)


# Account view
@login_required(login_url='logout_view')
@permission_required('finance.can_view_profile', login_url='logout')
def account_view(request, username, title):
    user = User.objects.get(username=username)
    account = Account.objects.get(user=request.user, title=title)
    outcomes = Charge.get_outcomes(account)
    incomes = Charge.get_incomes(account)
    months = Charge.get_by_month(account)
    return render(request, 'account.html', {'user': user,
                                            'account': account,
                                            'incomes': incomes,
                                            'outcomes': outcomes,
                                            'months': months})


@login_required(login_url='login')
@api_view(['GET'])
def serialized_account_view(request, username, title):
    user = User.objects.get(username=username)
    account = Account.objects.get(user=user, title=title)
    serializer = AccountSerializer(account)
    return Response(serializer.data, status=status.HTTP_200_OK)


# All user's accounts
@login_required(login_url='logout_view')
@permission_required('finance.can_view_profile', login_url='logout_view')
def get_all_accounts(request, username):
    user = User.objects.get(username=username)
    all_accounts = Account.objects.filter(user=user)
    print("All accounts: ")
    print(all_accounts)
    return render(request, 'all_accounts.html', {'all_accounts': all_accounts,
                                                 'user': user})


@login_required(login_url='login')
@api_view(['GET'])
def serialized_get_all_accounts(request, username):
    user = User.objects.get(username=username)
    all_accounts = Account.objects.filter(user=user)
    serializer = AccountSerializer(all_accounts, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Charges of account
@login_required(login_url='logout_view')
@permission_required('finance.can_view_profile', login_url='logout_view')
def charges(request, username, title):
    user = User.objects.get(username=username)
    account = Account.objects.get(user=user, title=title)
    incomes = Charge.get_incomes(account)
    outcomes = Charge.get_outcomes(account)
    return render(request, 'charges.html', {'user': user,
                                            'account': account,
                                            'incomes': incomes,
                                            'outcomes': outcomes})


@login_required(login_url='login')
@api_view(['GET'])
def serialized_charges(request, username, title):
    user = User.objects.get(username=username)
    all_charges = Charge.objects.filter(account__title=account)
    serializer = ChargeSerializer(all_charges, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Create the charge
@login_required(login_url='logout_view')
@permission_required('finance.can_view_profile', login_url='logout_view')
def create_charge(request, username, title):
    user = User.objects.get(username=username)
    account = Account.objects.get(title=title)
    form = ChargeForm()
    if request.method == 'POST':
        form = ChargeForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                charge = Charge(account=account,
                                date=form.cleaned_data['date'],
                                value=form.cleaned_data['value'])
                charge.save()
                Account.objects.filter(user=user, title=title) \
                    .update(total=F('total') + form.cleaned_data['value'])
            return redirect('account_view',username, title)
    context = {'account': title, 'form': form}
    return render(request, 'charge.html', context)


# Charges by months
@login_required(login_url='logout_view')
@permission_required('finance.can_view_profile', login_url='logout_view')
def months(request, username, title):
    try:
        user = User.objects.get(username=username)
        account = Account.objects.get(user=user, title=title)
        by_months = Charge.get_by_month(account)
    except ObjectDoesNotExist:
        print("Can't find")
    return render(request, 'months.html', {'user': user,'account': account, 'months': by_months})


@login_required(login_url='login')
@api_view(['GET'])
def serialized_months(request, username, title):
    user = User.objects.get(username=username)
    account = Account.objects.get(user=user, title=title)
    test = MonthStatCollection(account)
    return test.get(request)

