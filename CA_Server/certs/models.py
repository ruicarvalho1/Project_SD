from django.db import models

class UserCertificate(models.Model):
    user_id = models.IntegerField()
    certificate_pem = models.TextField()
    issuer = models.CharField(max_length=500, null=True)
    serial_number = models.CharField(max_length=200, null=True)

    def __str__(self):
        return f"Certificate {self.id} for user {self.user_id}"
