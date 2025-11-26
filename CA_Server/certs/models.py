from django.db import models

class UserCertificate(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.TextField()
    certificate_pem = models.TextField()
    serial_number = models.CharField(max_length=256, unique=True)
    def __str__(self):
        return f"Certificate {self.id} for user {self.user_id}"

class CACertificate(models.Model):
    ca_cert_id = models.AutoField(primary_key=True)
    ca_cert = models.TextField()
    serial_number = models.CharField(max_length=256, unique=True)
    def __str__(self):
            return f"CA Certificate {self.serial_number}"

