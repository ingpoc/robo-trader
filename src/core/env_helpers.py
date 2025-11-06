"""
Helper utilities for managing environment variables and OAuth tokens.
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
from loguru import logger


def find_env_file() -> Path:
    """Find the .env file in the project root."""
    current = Path.cwd()
    env_file = current / ".env"

    # Look up the directory tree for .env file
    while not env_file.exists() and current.parent != current:
        current = current.parent
        env_file = current / ".env"

    return env_file


async def update_env_file(key: str, value: str) -> bool:
    """
    Update or add an environment variable in the .env file.

    Args:
        key: Environment variable name
        value: Value to set

    Returns:
        True if successful, False otherwise
    """
    try:
        env_file = find_env_file()

        # Read existing .env file
        content = ""
        if env_file.exists():
            async with aiofiles.open(env_file, "r") as f:
                content = await f.read()

        # Update or add the key-value pair
        lines = content.split("\n")
        updated = False
        new_lines = []

        for line in lines:
            # Match lines like "KEY=value" or "KEY='value'" or "KEY=\"value\""
            match = re.match(rf"^{re.escape(key)}=(.*)$", line.strip())
            if match:
                new_lines.append(f"{key}={value}")
                updated = True
            else:
                new_lines.append(line)

        # If key wasn't found, add it
        if not updated:
            new_lines.append(f"{key}={value}")

        # Write back to file
        async with aiofiles.open(env_file, "w") as f:
            await f.write("\n".join(new_lines))

        logger.info(f"Updated {key} in .env file")
        return True

    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        return False


async def save_zerodha_token_to_env(token_data: Dict[str, Any]) -> bool:
    """
    Save Zerodha OAuth token data to .env file.

    Args:
        token_data: Dictionary containing access_token, user_id, expires_at, etc.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Save access token
        access_token = token_data.get("access_token")
        if access_token:
            await update_env_file("ZERODHA_ACCESS_TOKEN", access_token)

        # Save user_id if available
        user_id = token_data.get("user_id")
        if user_id:
            await update_env_file("ZERODHA_USER_ID", user_id)

        # Save expires_at timestamp
        expires_at = token_data.get("expires_at")
        if expires_at:
            await update_env_file("ZERODHA_TOKEN_EXPIRES_AT", expires_at)

        logger.info(f"Saved Zerodha OAuth token to .env file for user: {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to save Zerodha token to .env: {e}")
        return False


def get_zerodha_token_from_env() -> Optional[Dict[str, Any]]:
    """
    Get Zerodha OAuth token from environment variables.

    Returns:
        Dictionary with token data if valid, None otherwise
    """
    try:
        access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        if not access_token:
            return None

        user_id = os.getenv("ZERODHA_USER_ID", "")
        expires_at_str = os.getenv("ZERODHA_TOKEN_EXPIRES_AT")

        # Check if token is expired
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) >= expires_at:
                    logger.info("Zerodha access token from ENV has expired")
                    return None
            except Exception as e:
                logger.warning(f"Could not parse token expiry: {e}")

        return {
            "access_token": access_token,
            "user_id": user_id,
            "expires_at": expires_at_str or datetime.now(timezone.utc).isoformat(),
            "login_time": datetime.now(timezone.utc).isoformat(),
            "source": "env",
        }

    except Exception as e:
        logger.error(f"Failed to get Zerodha token from ENV: {e}")
        return None


async def remove_zerodha_token_from_env() -> bool:
    """Remove Zerodha tokens from .env file."""
    try:
        keys_to_remove = [
            "ZERODHA_ACCESS_TOKEN",
            "ZERODHA_USER_ID",
            "ZERODHA_TOKEN_EXPIRES_AT",
        ]

        env_file = find_env_file()
        if not env_file.exists():
            return True

        async with aiofiles.open(env_file, "r") as f:
            content = await f.read()

        lines = content.split("\n")
        new_lines = []

        for line in lines:
            should_remove = False
            for key in keys_to_remove:
                if re.match(rf"^{re.escape(key)}=", line.strip()):
                    should_remove = True
                    break
            if not should_remove:
                new_lines.append(line)

        async with aiofiles.open(env_file, "w") as f:
            await f.write("\n".join(new_lines))

        logger.info("Removed Zerodha tokens from .env file")
        return True

    except Exception as e:
        logger.error(f"Failed to remove Zerodha tokens from .env: {e}")
        return False
