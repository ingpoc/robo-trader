"""
Secure token storage service for Kite Connect OAuth tokens.

This service handles secure storage, retrieval, and management of
OAuth tokens with encryption and automatic refresh capabilities.
"""

import asyncio
import logging
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.core.database_state.real_time_trading_state import KiteSession


class TokenStorageService:
    """Secure token storage and management service."""

    def __init__(self, encryption_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)

        # Initialize encryption
        if encryption_key:
            self.cipher_suite = Fernet(encryption_key.encode())
        else:
            # Generate a key from environment variables or use default
            self.cipher_suite = self._generate_cipher_suite()

    def _generate_cipher_suite(self) -> Fernet:
        """Generate encryption key from environment or create new one."""
        import os
        import hashlib

        # Try to get consistent key from environment
        key_material = os.getenv('ROBO_TRADER_ENCRYPTION_KEY', 'robo-trader-default-key')

        # Use PBKDF2 to derive a proper encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'robo-trader-salt',  # Fixed salt for consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_material.encode()))

        return Fernet(key)

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        try:
            encrypted = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Failed to encrypt data: {e}")
            raise TradingError(
                "Data encryption failed",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH
            )

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Failed to decrypt data: {e}")
            raise TradingError(
                "Data decryption failed",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH
            )

    def encrypt_token_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive token data."""
        try:
            encrypted_data = session_data.copy()

            # Encrypt sensitive fields
            sensitive_fields = [
                'public_token', 'access_token', 'refresh_token',
                'enctoken', 'api_secret'
            ]

            for field in sensitive_fields:
                if field in encrypted_data and encrypted_data[field]:
                    encrypted_data[field] = self.encrypt_data(encrypted_data[field])

            return encrypted_data

        except Exception as e:
            self.logger.error(f"Failed to encrypt token data: {e}")
            raise TradingError(
                "Token data encryption failed",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH
            )

    def decrypt_token_data(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive token data."""
        try:
            decrypted_data = encrypted_data.copy()

            # Decrypt sensitive fields
            sensitive_fields = [
                'public_token', 'access_token', 'refresh_token',
                'enctoken', 'api_secret'
            ]

            for field in sensitive_fields:
                if field in decrypted_data and decrypted_data[field]:
                    try:
                        decrypted_data[field] = self.decrypt_data(decrypted_data[field])
                    except Exception as decrypt_error:
                        self.logger.warning(f"Failed to decrypt field {field}: {decrypt_error}")
                        decrypted_data[field] = None

            return decrypted_data

        except Exception as e:
            self.logger.error(f"Failed to decrypt token data: {e}")
            raise TradingError(
                "Token data decryption failed",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH
            )

    def create_session_from_kite_data(self, account_id: str, kite_data: Dict[str, Any]) -> KiteSession:
        """Create KiteSession from Kite Connect response data."""
        try:
            # Calculate expiry (Kite sessions typically last for 24 hours)
            expires_at = datetime.now() + timedelta(hours=24)

            return KiteSession(
                account_id=account_id,
                user_id=kite_data.get('user_id'),
                public_token=kite_data.get('public_token'),
                access_token=kite_data.get('access_token'),
                refresh_token=kite_data.get('refresh_token'),
                enctoken=kite_data.get('enctoken'),
                user_type=kite_data.get('user_type'),
                email=kite_data.get('email'),
                user_name=kite_data.get('user_name'),
                user_shortname=kite_data.get('user_shortname'),
                avatar_url=kite_data.get('avatar_url'),
                broker=kite_data.get('broker', 'ZERODHA'),
                products=json.dumps(kite_data.get('products', [])),
                exchanges=json.dumps(kite_data.get('exchanges', [])),
                active=True,
                expires_at=expires_at.isoformat(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                last_used_at=datetime.now().isoformat()
            )

        except Exception as e:
            self.logger.error(f"Failed to create session from Kite data: {e}")
            raise TradingError(
                "Failed to create session from Kite data",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH
            )

    def prepare_session_for_storage(self, session: KiteSession) -> Dict[str, Any]:
        """Prepare session data for secure storage."""
        try:
            session_dict = {
                'account_id': session.account_id,
                'user_id': session.user_id,
                'public_token': session.public_token,
                'access_token': session.access_token,
                'refresh_token': session.refresh_token,
                'enctoken': session.enctoken,
                'user_type': session.user_type,
                'email': session.email,
                'user_name': session.user_name,
                'user_shortname': session.user_shortname,
                'avatar_url': session.avatar_url,
                'broker': session.broker,
                'products': session.products,
                'exchanges': session.exchanges,
                'active': session.active,
                'expires_at': session.expires_at,
                'created_at': session.created_at,
                'updated_at': session.updated_at,
                'last_used_at': session.last_used_at
            }

            return self.encrypt_token_data(session_dict)

        except Exception as e:
            self.logger.error(f"Failed to prepare session for storage: {e}")
            raise TradingError(
                "Failed to prepare session for storage",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH
            )

    def restore_session_from_storage(self, encrypted_data: Dict[str, Any]) -> KiteSession:
        """Restore session from encrypted storage data."""
        try:
            decrypted_data = self.decrypt_token_data(encrypted_data)

            return KiteSession(
                account_id=decrypted_data['account_id'],
                user_id=decrypted_data.get('user_id'),
                public_token=decrypted_data.get('public_token'),
                access_token=decrypted_data.get('access_token'),
                refresh_token=decrypted_data.get('refresh_token'),
                enctoken=decrypted_data.get('enctoken'),
                user_type=decrypted_data.get('user_type'),
                email=decrypted_data.get('email'),
                user_name=decrypted_data.get('user_name'),
                user_shortname=decrypted_data.get('user_shortname'),
                avatar_url=decrypted_data.get('avatar_url'),
                broker=decrypted_data.get('broker', 'ZERODHA'),
                products=decrypted_data.get('products'),
                exchanges=decrypted_data.get('exchanges'),
                active=decrypted_data.get('active', True),
                expires_at=decrypted_data.get('expires_at'),
                created_at=decrypted_data.get('created_at'),
                updated_at=decrypted_data.get('updated_at'),
                last_used_at=decrypted_data.get('last_used_at')
            )

        except Exception as e:
            self.logger.error(f"Failed to restore session from storage: {e}")
            raise TradingError(
                "Failed to restore session from storage",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH
            )

    def is_token_expired(self, session: KiteSession, buffer_minutes: int = 5) -> bool:
        """Check if token is expired or about to expire."""
        try:
            if not session.expires_at:
                return True

            expiry = datetime.fromisoformat(session.expires_at.replace('Z', '+00:00'))
            buffer_time = timedelta(minutes=buffer_minutes)

            return datetime.now() >= (expiry - buffer_time)

        except Exception as e:
            self.logger.error(f"Failed to check token expiry: {e}")
            return True  # Assume expired on error

    def update_session_usage(self, session: KiteSession) -> KiteSession:
        """Update session usage timestamps."""
        try:
            session.last_used_at = datetime.now().isoformat()
            session.updated_at = datetime.now().isoformat()
            return session

        except Exception as e:
            self.logger.error(f"Failed to update session usage: {e}")
            return session

    def validate_session(self, session: KiteSession) -> Dict[str, Any]:
        """Validate session and return status information."""
        try:
            validation_result = {
                'valid': False,
                'expires_at': session.expires_at,
                'time_to_expiry': None,
                'warnings': [],
                'errors': []
            }

            # Check if session has required fields
            required_fields = ['access_token', 'public_token', 'account_id']
            for field in required_fields:
                if not getattr(session, field, None):
                    validation_result['errors'].append(f"Missing required field: {field}")

            # Check expiry
            if session.expires_at:
                try:
                    expiry = datetime.fromisoformat(session.expires_at.replace('Z', '+00:00'))
                    now = datetime.now()
                    time_to_expiry = expiry - now

                    validation_result['time_to_expiry'] = {
                        'hours': int(time_to_expiry.total_seconds() // 3600),
                        'minutes': int((time_to_expiry.total_seconds() % 3600) // 60),
                        'seconds': int(time_to_expiry.total_seconds() % 60)
                    }

                    # Add warnings for sessions expiring soon
                    if time_to_expiry < timedelta(minutes=30):
                        validation_result['warnings'].append("Session expires in less than 30 minutes")
                    elif time_to_expiry < timedelta(hours=2):
                        validation_result['warnings'].append("Session expires in less than 2 hours")

                    # Check if expired
                    if time_to_expiry <= timedelta(0):
                        validation_result['errors'].append("Session has expired")
                    else:
                        validation_result['valid'] = True

                except ValueError as e:
                    validation_result['errors'].append(f"Invalid expiry format: {e}")
            else:
                validation_result['errors'].append("No expiry information available")

            return validation_result

        except Exception as e:
            self.logger.error(f"Failed to validate session: {e}")
            return {
                'valid': False,
                'expires_at': session.expires_at,
                'time_to_expiry': None,
                'warnings': [],
                'errors': [f"Validation failed: {e}"]
            }

    def mask_sensitive_data(self, session: KiteSession) -> Dict[str, Any]:
        """Create a version of session with sensitive data masked."""
        try:
            def mask_token(token: Optional[str]) -> Optional[str]:
                if not token or len(token) < 8:
                    return "***"
                return token[:4] + "*" * (len(token) - 8) + token[-4:]

            return {
                'account_id': session.account_id,
                'user_id': session.user_id,
                'public_token': mask_token(session.public_token),
                'access_token': mask_token(session.access_token),
                'refresh_token': mask_token(session.refresh_token),
                'enctoken': mask_token(session.enctoken),
                'user_type': session.user_type,
                'email': session.email,
                'user_name': session.user_name,
                'user_shortname': session.user_shortname,
                'avatar_url': session.avatar_url,
                'broker': session.broker,
                'products': session.products,
                'exchanges': session.exchanges,
                'active': session.active,
                'expires_at': session.expires_at,
                'created_at': session.created_at,
                'updated_at': session.updated_at,
                'last_used_at': session.last_used_at
            }

        except Exception as e:
            self.logger.error(f"Failed to mask sensitive data: {e}")
            return {}