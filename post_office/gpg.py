from django.core.mail import EmailMessage, EmailMultiAlternatives, SafeMIMEMultipart
from email.mime.application import MIMEApplication
from email.encoders import encode_7or8bit


def find_public_keys_for_encryption(primary):
    """
    A function that isolates a (or some) subkey(s) from a primary key 
    (if it has any) based on its usage flags, looking for the one(s) that can
    be used for encryption. 
    It returns an empty list if it cannot find any.
    """
    try:
        from pgpy.constants import KeyFlags
    except ImportError:
        raise ModuleNotFoundError('GPG encryption requires pgpy module')

    encryption_keys = []
    if not primary:
        return encryption_keys
    for k in primary.subkeys.keys():
        subkey = primary.subkeys[k]
        flags = subkey._get_key_flags()
        if KeyFlags.EncryptCommunications in flags and KeyFlags.EncryptStorage in flags:
            encryption_keys.append(subkey)

    return encryption_keys


def find_public_key_for_recipient(pubkeys, recipient):
    """
    A function that looks through a list of valid public keys (validated using parse_public_keys)
    trying to match the email of the given recipient.
    """
    for pubkey in pubkeys:
        for userid in pubkey.userids:
            if userid.email == recipient:
                return pubkey
    return None


def encrypt_with_pubkeys(_pubkeys, payload):
    try:
        from pgpy.constants import SymmetricKeyAlgorithm
    except ImportError:
        raise ModuleNotFoundError('GPG encryption requires pgpy module')

    pubkeys = []
    for pubkey in _pubkeys:
        suitable = find_public_keys_for_encryption(pubkey)
        if suitable:
            pubkeys.extend(suitable)

    if len(pubkeys) < 1:
        return payload
    elif len(pubkeys) == 1:
        return pubkeys[0].encrypt(payload)

    cipher = SymmetricKeyAlgorithm.AES256
    skey = cipher.gen_key()
    
    for pubkey in pubkeys:
        payload = pubkey.encrypt(payload, cipher=cipher, sessionkey=skey)

    del skey
    return payload


class EncryptedEmailMessage(EmailMessage):
    """
    A class representing an RFC3156 compliant MIME multipart message containing
    an OpenPGP-encrypted simple email message. 
    """
    def __init__(self, pubkeys=None, **kwargs):
        super().__init__(**kwargs)

        try:
            from pgpy import PGPKey
        except ImportError:
            raise ModuleNotFoundError('GPG encryption requires pgpy module')

        if pubkeys:
            self.pubkeys = [PGPKey.from_blob(pubkey)[0] \
                for pubkey in pubkeys]
        else:
            raise ValueError('EncryptedEmailMessage requires a non-null and non-empty list of gpg public keys')


    def _create_message(self, msg):
        try:
            from pgpy import PGPMessage
        except ImportError:
            raise ModuleNotFoundError('GPG encryption requires pgpy module')
        
        msg = super()._create_message(msg)

        payload = PGPMessage.new(msg.as_string())
        payload = encrypt_with_pubkeys(self.pubkeys, payload)

        control = MIMEApplication(
            "Version: 1", 
            _subtype='pgp-encrypted', 
            _encoder=encode_7or8bit
        )
        data = MIMEApplication(
            str(payload),  
            _encoder=encode_7or8bit
        )
        msg = SafeMIMEMultipart(
            _subtype='encrypted',
            _subparts=[control, data],
            protocol='application/pgp-encrypted'
        )

        return msg


class EncryptedEmailMultiAlternatives(EmailMultiAlternatives):
    """
    A class representing an RFC3156 compliant MIME multipart message containing
    an OpenPGP-encrypted multipart/alternative email message (with multiple 
    versions e.g. plain text and html).
    """
    def __init__(self, pubkeys=None, **kwargs):
        super().__init__(**kwargs)

        try:
            from pgpy import PGPKey
        except ImportError:
            raise ModuleNotFoundError('GPG encryption requires pgpy module')

        if pubkeys:
            self.pubkeys = [PGPKey.from_blob(pubkey)[0] for pubkey in pubkeys]
        else:
            raise ValueError('EncryptedEmailMultiAlternatives requires a non-null and non-empty list of gpg public keys')


    def _create_message(self, msg):
        try:
            from pgpy import PGPMessage
        except ImportError:
            raise ModuleNotFoundError('GPG encryption requires pgpy module')
        
        msg = super()._create_message(msg)

        payload = PGPMessage.new(msg.as_string())
        payload = encrypt_with_pubkeys(self.pubkeys, payload)

        control = MIMEApplication(
            "Version: 1", 
            _subtype='pgp-encrypted', 
            _encoder=encode_7or8bit
        )
        data = MIMEApplication(
            str(payload),  
            _encoder=encode_7or8bit
        )
        msg = SafeMIMEMultipart(
            _subtype='encrypted',
            _subparts=[control, data],
            protocol='application/pgp-encrypted'
        )

        return msg