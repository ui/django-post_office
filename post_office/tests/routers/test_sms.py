from django.core.exceptions import ValidationError
from django.test import TestCase

from ...routers.sms import send, validate_phonenumber, validate_phonenumbers


class SMSTest(TestCase):

    def test_validate_phonenumber(self):
        """Test basic phonenumber validation"""
        self.assertTrue(validate_phonenumber('+6123981239'))
        self.assertTrue(validate_phonenumber('6123981239'))
        self.assertRaises(ValidationError, validate_phonenumber, 'abc')

    def test_validate_phonenumbers(self):
        """validate_phonenumbers() accepts single or multiple phonenumbers."""
        self.assertTrue(validate_phonenumbers('+6123981239'))
        self.assertTrue(validate_phonenumbers(['+6123981239', '+6123981239']))
        self.assertRaises(ValidationError,
                          validate_phonenumbers, ['+6123981239', '+a'])

    def test_send(self):
        """ """
        sender = '+1232138'
        recipient = '123333'
        email = send(recipient=recipient, sender=sender, message='Test')
        self.assertEqual(email.from_email, sender)
        self.assertEqual(email.to, [recipient])
        email_message = email.email_message()

        self.assertEqual(email_message.from_email, sender)
        self.assertEqual(email_message.to, [recipient])
