from email.mime.multipart import MIMEMultipart
from django.core.mail import EmailMessage, EmailMultiAlternatives, SafeMIMEMultipart
from email.mime.application import MIMEApplication
from email.encoders import encode_7or8bit, encode_quopri
from email import charset

from .settings import get_signing_key_path, get_signing_key_passphrase


utf8_charset_qp = charset.Charset('utf-8')
utf8_charset_qp.body_encoding = charset.QP


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


def find_private_key_for_signing(primary):
    """
    A function that returns the primary key or one of its subkeys, ensured
    to be the most recent key the can be used for signing. 
    """
    try:
        from pgpy.constants import KeyFlags
    except ImportError:
        raise ModuleNotFoundError('GPG encryption requires pgpy module')

    if not primary:
        return None

    most_recent_signing_key = None
    for k in primary.subkeys.keys():
        subkey = primary.subkeys[k]
        flags = subkey._get_key_flags()
        if KeyFlags.Sign in flags and (not most_recent_signing_key or \
                most_recent_signing_key.created < subkey.created):
            most_recent_signing_key = subkey

    return most_recent_signing_key if most_recent_signing_key else primary


def find_public_key_for_recipient(pubkeys, recipient):
    """
    A function that looks through a list of valid public keys (validated using validate_public_keys)
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


def sign_with_privkey(_privkey, payload):
    privkey = find_private_key_for_signing(_privkey)
    if not privkey:
        return payload

    if not privkey.is_unlocked:
        raise ValueError('The selected signing private key is locked')

    return privkey.sign(payload)


def process_message(msg, pubkeys, privkey):
    """
    Apply signature and/or encryption to the given message payload.
    This function also applies the Quoted-Printable transfer encoding to
    both multipart and non-multipart messages and replaces newline characters
    with the <CR><LF> sequences, as per RFC 3156. 
    A rather rustic workaround has been put in place to prevent the leading 
    '\n ' sequence of the boundary parameter in the Content-Type header to
    invalidate the signature.
    """
    try:
        from pgpy import PGPMessage
    except ImportError:
        raise ModuleNotFoundError('GPG encryption requires pgpy module')

    if msg.is_multipart:
        for payload in msg.get_payload():
            del payload['Content-Transfer-Encoding']
            encode_quopri(payload)
    else:
        del msg['Content-Transfer-Encoding']
        encode_quopri(msg)

    payload = msg.as_string().replace(
        '\n boundary', ' boundary'
    ).replace('\n', '\r\n')

    if privkey:
        if privkey.is_unlocked:
            signature = privkey.sign(payload)
        else:
            passphrase = get_signing_key_passphrase()
            if not passphrase:
                raise ValueError('No key passphrase found to unlock, cannot sign')
            with privkey.unlock(passphrase):
                signature = privkey.sign(payload)
            del passphrase

        signature = MIMEApplication(
            str(signature),
            _subtype='pgp-signature',
            _encoder=encode_7or8bit
        )
        msg = SafeMIMEMultipart(
            _subtype='signed',
            _subparts=[msg, signature],
            micalg='pgp-sha256',
            protocol='application/pgp-signature'
        )

    if pubkeys:
        payload = encrypt_with_pubkeys(
            pubkeys, PGPMessage.new(str(msg))
        )

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


class EncryptedOrSignedEmailMessage(EmailMessage):
    """
    A class representing an RFC3156 compliant MIME multipart message containing
    an OpenPGP-encrypted simple email message. 
    """
    def __init__(self, pubkeys=None, sign_with_privkey=False, **kwargs):
        super().__init__(**kwargs)

        try:
            from pgpy import PGPKey
        except ImportError:
            raise ModuleNotFoundError('GPG encryption requires pgpy module')

        if pubkeys:
            self.pubkeys = [PGPKey.from_blob(pubkey)[0] \
                for pubkey in pubkeys]
        else:
            self.pubkeys = []
        
        if sign_with_privkey:
            path = get_signing_key_path()
            if not path:
                raise ValueError('No key path found, cannot sign message')
            self.privkey = find_private_key_for_signing(
                PGPKey.from_file(path)[0]
            )
        else:
            self.privkey = None

        if not self.pubkeys and not self.privkey:
            raise ValueError('EncryptedOrSignedEmailMessage requires either a non-null and non-empty list of gpg public keys or a valid private key')

    def _create_message(self, msg):    
        msg = super()._create_message(msg)
        return process_message(msg, self.pubkeys, self.privkey)


class EncryptedOrSignedEmailMultiAlternatives(EmailMultiAlternatives):
    """
    A class representing an RFC3156 compliant MIME multipart message containing
    an OpenPGP-encrypted multipart/alternative email message (with multiple 
    versions e.g. plain text and html).
    """
    def __init__(self, pubkeys=None, sign_with_privkey=False, **kwargs):
        super().__init__(**kwargs)

        try:
            from pgpy import PGPKey
        except ImportError:
            raise ModuleNotFoundError('GPG encryption requires pgpy module')

        if pubkeys:
            self.pubkeys = [PGPKey.from_blob(pubkey)[0] \
                for pubkey in pubkeys]
        else:
            self.pubkeys = []
        
        if sign_with_privkey:
            path = get_signing_key_path()
            if not path:
                raise ValueError('No key path found, cannot sign message')
            self.privkey = find_private_key_for_signing(
                PGPKey.from_file(path)[0]
            )
        else:
            self.privkey = None

        if not self.pubkeys and not self.privkey:
            raise ValueError('EncryptedOrSignedEmailMultiAlternatives requires either a non-null and non-empty list of gpg public keys or a valid private key')

    def _create_message(self, msg):
        msg = super()._create_message(msg)
        return process_message(msg, self.pubkeys, self.privkey)