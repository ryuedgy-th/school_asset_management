# -*- coding: utf-8 -*-

import logging
import secrets
from typing import Optional, Tuple
from datetime import datetime, timedelta
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    _logger.warning('Redis library not available. Rate limiting will use fallback mode.')


class SignatureSecurityHelper:
    """Redis-based rate limiting for signature endpoints.

    Implements distributed rate limiting using Redis as shared storage
    to work correctly in multi-worker production environments.

    Fallback Mechanism:
        If Redis is unavailable, the system will log a warning and allow
        the request to proceed (fail-open for availability).

    Configuration Parameters (ir.config_parameter):
        - school_asset.redis_host (default: localhost)
        - school_asset.redis_port (default: 6379)
        - school_asset.redis_db (default: 0)
        - school_asset.redis_password (optional)
        - school_asset.rate_limit_requests (default: 10)
        - school_asset.rate_limit_window_seconds (default: 3600)
    """

    # Default configuration
    DEFAULT_MAX_ATTEMPTS = 10
    DEFAULT_WINDOW_SECONDS = 3600  # 1 hour
    REDIS_KEY_PREFIX = 'school_asset:rate_limit'
    REDIS_CONNECTION_TIMEOUT = 2  # seconds

    def __init__(self, env):
        """Initialize Redis connection with fallback mechanism.

        Args:
            env: Odoo environment object for accessing configuration
        """
        self.env = env
        self._redis_client = None
        self._redis_available = REDIS_AVAILABLE

    def _get_config_param(self, key: str, default: str = '') -> str:
        """Get configuration parameter from ir.config_parameter.

        Args:
            key: Configuration parameter key
            default: Default value if parameter not found

        Returns:
            str: Configuration value
        """
        try:
            return self.env['ir.config_parameter'].sudo().get_param(key, default)
        except Exception as e:
            _logger.error(f'Error retrieving config parameter {key}: {e}')
            return default

    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection pooling.

        Returns:
            redis.Redis: Redis client instance or None if unavailable
        """
        if not self._redis_available:
            return None

        # Return existing connection if available
        if self._redis_client is not None:
            try:
                # Test connection
                self._redis_client.ping()
                return self._redis_client
            except (redis.ConnectionError, redis.TimeoutError) as e:
                _logger.warning(f'Redis connection lost: {e}')
                self._redis_client = None

        # Create new connection
        try:
            redis_host = self._get_config_param('school_asset.redis_host', 'localhost')
            redis_port = int(self._get_config_param('school_asset.redis_port', '6379'))
            redis_db = int(self._get_config_param('school_asset.redis_db', '0'))
            redis_password = self._get_config_param('school_asset.redis_password', '')

            connection_kwargs = {
                'host': redis_host,
                'port': redis_port,
                'db': redis_db,
                'socket_connect_timeout': self.REDIS_CONNECTION_TIMEOUT,
                'socket_timeout': self.REDIS_CONNECTION_TIMEOUT,
                'decode_responses': True,
            }

            if redis_password:
                connection_kwargs['password'] = redis_password

            self._redis_client = redis.Redis(**connection_kwargs)

            # Test connection
            self._redis_client.ping()
            _logger.info(f'Redis connection established: {redis_host}:{redis_port}/{redis_db}')

            return self._redis_client

        except (redis.ConnectionError, redis.TimeoutError, ValueError) as e:
            _logger.warning(f'Failed to connect to Redis: {e}. Using fallback mode.')
            self._redis_client = None
            return None

    def _get_redis_key(self, ip_address: str, endpoint: str = 'signature') -> str:
        """Generate Redis key for rate limiting.

        Args:
            ip_address: Client IP address
            endpoint: API endpoint being accessed

        Returns:
            str: Redis key in format "school_asset:rate_limit:{ip}:{endpoint}"
        """
        # Sanitize IP address (IPv6 compatibility)
        sanitized_ip = ip_address.replace(':', '_')
        return f'{self.REDIS_KEY_PREFIX}:{sanitized_ip}:{endpoint}'

    @api.model
    def check_rate_limit(self, ip_address: str, endpoint: str = 'signature') -> Tuple[bool, int]:
        """Check if request is within rate limit.

        Args:
            ip_address: Client IP address
            endpoint: API endpoint being accessed

        Returns:
            Tuple[bool, int]: (is_allowed, attempts_remaining)
                - is_allowed: True if request is within limit
                - attempts_remaining: Number of remaining attempts

        Raises:
            UserError: If rate limit is exceeded (for user-facing endpoints)
        """
        # Get rate limit configuration
        max_attempts = int(self._get_config_param(
            'school_asset.rate_limit_requests',
            str(self.DEFAULT_MAX_ATTEMPTS)
        ))
        window_seconds = int(self._get_config_param(
            'school_asset.rate_limit_window_seconds',
            str(self.DEFAULT_WINDOW_SECONDS)
        ))

        # Get Redis client
        redis_client = self._get_redis_client()

        if redis_client is None:
            # Fallback mode: allow request but log warning
            _logger.warning(
                f'Rate limiting unavailable (Redis down). Allowing request from {ip_address}'
            )
            return True, max_attempts - 1

        try:
            redis_key = self._get_redis_key(ip_address, endpoint)
            now_timestamp = int(datetime.now().timestamp())
            cutoff_timestamp = now_timestamp - window_seconds

            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()

            # Remove old attempts (older than window)
            pipe.zremrangebyscore(redis_key, '-inf', cutoff_timestamp)

            # Count current attempts in window
            pipe.zcard(redis_key)

            # Execute pipeline
            pipe.execute()

            # Get current attempt count
            current_attempts = redis_client.zcard(redis_key)

            # Check if limit exceeded
            if current_attempts >= max_attempts:
                _logger.warning(
                    f'Rate limit exceeded for IP {ip_address} on endpoint {endpoint}. '
                    f'Attempts: {current_attempts}/{max_attempts}'
                )

                # Log to security audit
                self._log_rate_limit_exceeded(ip_address, endpoint, current_attempts)

                return False, 0

            # Record this attempt (use timestamp as both score and member for uniqueness)
            redis_client.zadd(
                redis_key,
                {f'{now_timestamp}_{current_attempts}': now_timestamp}
            )

            # Set expiration (TTL) to auto-cleanup
            redis_client.expire(redis_key, window_seconds)

            attempts_remaining = max_attempts - current_attempts - 1

            _logger.debug(
                f'Rate limit check passed for {ip_address}. '
                f'Attempts: {current_attempts + 1}/{max_attempts}, '
                f'Remaining: {attempts_remaining}'
            )

            return True, attempts_remaining

        except Exception as e:
            _logger.error(f'Error checking rate limit: {e}. Allowing request (fail-open).')
            return True, max_attempts - 1

    def _log_rate_limit_exceeded(self, ip_address: str, endpoint: str, attempts: int):
        """Log rate limit exceeded event to security audit.

        Args:
            ip_address: Client IP address
            endpoint: API endpoint
            attempts: Number of attempts
        """
        try:
            self.env['asset.security.audit.log'].sudo().log_security_event(
                event_type='rate_limit_exceeded',
                ip_address=ip_address,
                error_message=f'Rate limit exceeded on {endpoint} endpoint. Attempts: {attempts}',
                additional_info={'endpoint': endpoint, 'attempts': attempts}
            )
        except Exception as e:
            _logger.error(f'Failed to log rate limit event: {e}')

    @api.model
    def log_failed_attempt(self, ip_address: str, token: str, attempt_type: str = 'signature'):
        """Log failed signature attempt for security audit.

        Args:
            ip_address: Client IP address
            token: Token that was attempted
            attempt_type: Type of attempt (signature, approval, etc)
        """
        _logger.warning(
            f'Failed {attempt_type} attempt from IP {ip_address} with token {token[:8]}...'
        )

        try:
            self.env['asset.security.audit.log'].sudo().log_signature_attempt(
                event_type='signature_failed',
                signature_type=attempt_type,
                ip_address=ip_address,
                token=token,
                error_message=f'Failed {attempt_type} attempt'
            )
        except Exception as e:
            _logger.error(f'Failed to log security event: {e}')

    @api.model
    def ensure_signature_secret_exists(self):
        """Ensure that HMAC secret key exists and is properly generated.

        This method should be called during module installation and
        whenever token validation is performed.

        Returns:
            str: The secret key value
        """
        try:
            # Get current secret
            current_secret = self._get_config_param('school_asset.signature_secret')

            # Generate new secret if it doesn't exist or is the default placeholder
            if not current_secret or current_secret == 'CHANGE_ME_DURING_INSTALLATION':
                new_secret = secrets.token_hex(32)

                # Store the new secret
                self.env['ir.config_parameter'].sudo().set_param(
                    'school_asset.signature_secret',
                    new_secret
                )

                _logger.info('Generated new HMAC secret key for signature tokens')
                return new_secret

            return current_secret

        except Exception as e:
            _logger.error(f'Error managing signature secret: {e}')
            # Fallback: generate a temporary secret
            return secrets.token_hex(32)

    @api.model
    def get_signature_secret(self):
        """Get the HMAC secret key for token generation/validation.

        Returns:
            str: The secret key value
        """
        return self.ensure_signature_secret_exists()
