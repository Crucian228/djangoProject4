from django.conf import settings
from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.db.models import CASCADE, Avg
from django.db.models.functions import TruncMonth


class Account(models.Model):
    title = models.CharField(max_length=33, verbose_name='Название счета')
    description = models.TextField(blank=True)
    total = models.DecimalField(max_digits=6, decimal_places=2)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)

    def __str__(self):
        return str(self.title)


class Charge(models.Model):
    date = models.DateField()
    value = models.DecimalField(max_digits=6, decimal_places=2)
    account = models.ForeignKey(Account, on_delete=CASCADE)

    def __str__(self):
        return str(self.date) + ":" + str(self.value) + ":" + str(self.account)

    @classmethod
    def get_incomes(cls, account):
        return cls.objects.filter(account=account).filter(value__gte=0)

    @classmethod
    def get_outcomes(cls, account):
        return cls.objects.filter(account=account).filter(value__lt=0)

    @classmethod
    def get_by_month(cls, account):
        return cls.objects \
            .filter(account=account) \
            .annotate(month=TruncMonth('date')) \
            .values('month') \
            .annotate(c=Avg('value')) \
            .values('month', 'c')


class User(AbstractUser):

    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=300)