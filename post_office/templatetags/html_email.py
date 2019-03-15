# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from email.mime.image import MIMEImage
import hashlib
import os
from django import template
from django.contrib.staticfiles import finders
from django.core.files import File
from django.core.files.images import ImageFile

register = template.Library()


@register.simple_tag(takes_context=True)
def image_src(context, file):
    assert hasattr(context.template, '_attached_images'), \
        "You must use template engine 'html_email' when rendering images using templatetag 'image_src'."
    if isinstance(file, ImageFile):
        fileobj = file
    elif os.path.isabs(file) and os.path.exists(file):
        fileobj = File(open(file, 'rb'), name=file)
    else:
        absfilename = finders.find(file)
        if absfilename is None:
            raise FileNotFoundError("No such file: {}".format(file))
        fileobj = File(open(absfilename, 'rb'), name=file)
    raw_data = fileobj.read()
    image = MIMEImage(raw_data)
    md5sum = hashlib.md5(raw_data).hexdigest()
    image.add_header('Content-Disposition', 'inline', filename=md5sum)
    image.add_header('Content-ID', '<{}>'.format(md5sum))
    context.template._attached_images.append(image)
    return 'cid:{}'.format(md5sum)
