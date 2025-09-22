import threading
import weakref
from typing import Any, Dict


class LockManager:
    """
    Thread-safe lock manager for creating and managing locks based on key-value pairs.

    This class provides a centralized way to obtain locks for specific resources
    identified by a key-value combination. It ensures thread safety and includes
    cleanup mechanisms to prevent memory leaks.
    """

    def __init__(self) -> None:
        """Initialize a new LockManager instance."""
        self._locks: Dict[str, Dict[Any, threading.Lock]] = {}
        self._meta_lock = threading.RLock()  # Protects the locks dictionary itself

    def get_lock(self, key: str, value: str) -> threading.Lock:
        """
        Get a lock for the specified key-value pair.

        Returns the same lock instance for identical key-value combinations,
        ensuring proper synchronization across threads.

        Args:
            key: The resource category/type (must be non-empty string)
            value: The specific resource identifier within the category

        Returns:
            A threading.Lock instance for the key-value pair

        Raises:
            TypeError: If key is not a string
            ValueError: If key is empty or whitespace-only
        """
        if not isinstance(key, str):
            raise TypeError("Key must be a string")

        if not key.strip():
            raise ValueError("Key cannot be empty")

        with self._meta_lock:
            # Initialize key dictionary if it doesn't exist
            if key not in self._locks:
                self._locks[key] = {}

            # Initialize lock for value if it doesn't exist
            if value not in self._locks[key]:
                self._locks[key][value] = threading.Lock()

            return self._locks[key][value]

    def cleanup(self) -> None:
        """
        Remove locks that are no longer referenced.

        This method uses weak references to detect locks that are no longer
        in use and removes them from the internal storage to prevent memory leaks.

        Note: This is a best-effort cleanup. Some locks may still be retained
        if they are actively being used or referenced elsewhere.
        """
        with self._meta_lock:
            keys_to_remove = []

            for key, value_dict in self._locks.items():
                values_to_remove = []

                for value, lock in value_dict.items():
                    # Create a weak reference to check if the lock is still referenced
                    try:
                        weak_ref = weakref.ref(lock)
                        # If we can create a weak reference and it's the only reference
                        # (besides our local variable), mark it for removal
                        if weak_ref() is not None:
                            # Check reference count (2 = our local var + dict entry)
                            import sys

                            if (
                                sys.getrefcount(lock) <= 3
                            ):  # dict, local var, getrefcount param
                                values_to_remove.append(value)
                    except (TypeError, AttributeError):
                        # If we can't create weak reference, keep the lock
                        continue

                # Remove unused locks
                for value in values_to_remove:
                    del value_dict[value]

                # If no values left for this key, mark key for removal
                if not value_dict:
                    keys_to_remove.append(key)

            # Remove empty key dictionaries
            for key in keys_to_remove:
                del self._locks[key]


# Global instance for backward compatibility and ease of use
_default_lock_manager = LockManager()


def get_lock(key: str, value: str) -> threading.Lock:
    """
    Get a lock for the specified key-value pair using the default manager.

    This function provides backward compatibility with the original API
    while using the improved thread-safe implementation.

    Args:
        key: The resource category/type (must be non-empty string)
        value: The specific resource identifier within the category

    Returns:
        A threading.Lock instance for the key-value pair

    Raises:
        TypeError: If key is not a string
        ValueError: If key is empty or whitespace-only
    """
    return _default_lock_manager.get_lock(key, value)
