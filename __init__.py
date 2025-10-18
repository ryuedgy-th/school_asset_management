# -*- coding: utf-8 -*-

from . import models
from . import wizards
from . import reports
from . import controllers


def post_init_hook(env):
    """Post-initialization hook to generate secret key after module installation.

    Args:
        env: Odoo environment
    """
    import logging
    import secrets

    _logger = logging.getLogger(__name__)

    try:
        # Generate and store HMAC secret key if not exists
        config_param = env['ir.config_parameter'].sudo()
        current_secret = config_param.get_param('school_asset.signature_secret')

        if not current_secret or current_secret == 'CHANGE_ME_DURING_INSTALLATION':
            new_secret = secrets.token_hex(32)  # 64-character hex string (256 bits)
            config_param.set_param('school_asset.signature_secret', new_secret)
            _logger.info('Generated new HMAC-SHA256 secret key for signature tokens')
        else:
            _logger.info('HMAC secret key already exists')

        _logger.info('School Asset Management: Post-initialization completed successfully')

    except Exception as e:
        _logger.error(f'School Asset Management: Post-initialization failed: {e}')
        # Don't raise the exception to avoid blocking module installation
