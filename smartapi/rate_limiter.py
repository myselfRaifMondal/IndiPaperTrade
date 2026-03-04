"""
Rate Limiter for Angel One SmartAPI

This module implements rate limiting to comply with Angel One SmartAPI's
rate limit requirements and prevent 403 "Access denied" errors.

SmartAPI Rate Limits:
- Login API: 1 request/second
- getLtpData: 10 requests/second, 500 requests/minute
- Historical Candle: 3 requests/second
- Order APIs: 9 requests/second

The rate limiter uses a token bucket algorithm for efficient,
thread-safe rate limiting.

Usage:
    from smartapi.rate_limiter import RateLimiter
    
    limiter = RateLimiter(max_requests=10, time_window=1.0)
    
    with limiter:
        # Make API call
        response = api.get_ltp()
"""

import time
import threading
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API call throttling.
    
    Thread-safe implementation that prevents exceeding SmartAPI rate limits.
    
    Algorithm:
    - Maintains a "bucket" of tokens
    - Each API call consumes one token
    - Tokens are refilled at a constant rate
    - If bucket is empty, caller must wait
    
    Attributes:
        max_requests: Maximum requests allowed in time window
        time_window: Time window in seconds (e.g., 1.0 for per second)
        tokens: Current number of available tokens
        last_update: Timestamp of last token update
    """
    
    def __init__(self, max_requests: int, time_window: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds (default: 1.0)
        
        Example:
            # Allow 10 requests per second
            limiter = RateLimiter(max_requests=10, time_window=1.0)
            
            # Allow 500 requests per minute
            limiter = RateLimiter(max_requests=500, time_window=60.0)
        """
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if time_window <= 0:
            raise ValueError("time_window must be positive")
        
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = float(max_requests)  # Start with full bucket
        self.last_update = time.time()
        self.lock = threading.RLock()
        
        # Calculate rate of token refill
        self.refill_rate = max_requests / time_window
        
        logger.debug(
            f"Rate limiter initialized: {max_requests} requests "
            f"per {time_window} seconds"
        )
    
    def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time.
        
        Called internally before each request to update token count.
        """
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        self.tokens = min(
            self.max_requests,
            self.tokens + (elapsed * self.refill_rate)
        )
        
        self.last_update = now
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make one API call.
        
        Blocks until a token is available or timeout occurs.
        
        Args:
            timeout: Maximum seconds to wait (None = wait forever)
        
        Returns:
            bool: True if acquired, False if timeout
        
        Example:
            >>> limiter = RateLimiter(max_requests=10, time_window=1.0)
            >>> if limiter.acquire(timeout=5.0):
            ...     # Make API call
            ...     response = api.get_data()
            ... else:
            ...     print("Timeout waiting for rate limit")
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                self._refill_tokens()
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(
                        f"Token acquired. Remaining: {self.tokens:.2f}"
                    )
                    return True
                
                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.refill_rate
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed + wait_time > timeout:
                    logger.warning("Rate limiter timeout")
                    return False
            
            # Sleep until next token available
            time.sleep(min(wait_time, 0.1))  # Sleep in small increments
    
    @contextmanager
    def limit(self, timeout: Optional[float] = None):
        """
        Context manager for rate-limited operations.
        
        Usage:
            with limiter.limit():
                # Make API call
                response = api.get_data()
        
        Args:
            timeout: Maximum seconds to wait (None = wait forever)
        
        Raises:
            TimeoutError: If timeout occurs before token available
        """
        if not self.acquire(timeout=timeout):
            raise TimeoutError(
                f"Rate limiter timeout after {timeout} seconds"
            )
        try:
            yield
        finally:
            pass  # Token already consumed in acquire()
    
    def __enter__(self):
        """Support for 'with' statement."""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for 'with' statement."""
        return False
    
    def get_available_tokens(self) -> float:
        """
        Get current number of available tokens.
        
        Returns:
            float: Number of tokens currently available
        
        Example:
            >>> limiter = RateLimiter(max_requests=10, time_window=1.0)
            >>> print(f"Available: {limiter.get_available_tokens()}")
        """
        with self.lock:
            self._refill_tokens()
            return self.tokens
    
    def wait_time_for_token(self) -> float:
        """
        Calculate seconds to wait until next token available.
        
        Returns:
            float: Seconds to wait (0 if token immediately available)
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= 1.0:
                return 0.0
            
            return (1.0 - self.tokens) / self.refill_rate
    
    def reset(self) -> None:
        """
        Reset rate limiter to full capacity.
        
        Useful for testing or manual rate limit reset.
        """
        with self.lock:
            self.tokens = float(self.max_requests)
            self.last_update = time.time()
            logger.debug("Rate limiter reset")


class MultiRateLimiter:
    """
    Manages multiple rate limiters for different API endpoints.
    
    SmartAPI has different rate limits for different endpoints.
    This class manages all of them in one place.
    
    Attributes:
        limiters: Dictionary of endpoint -> RateLimiter
    """
    
    def __init__(self):
        """
        Initialize multi-rate limiter with SmartAPI limits.
        
        Default rate limits:
        - login: 1 request/second
        - ltp: 10 requests/second
        - historical: 3 requests/second
        - orders: 9 requests/second
        """
        self.limiters = {
            'login': RateLimiter(max_requests=1, time_window=1.0),
            'ltp': RateLimiter(max_requests=10, time_window=1.0),
            'ltp_minute': RateLimiter(max_requests=500, time_window=60.0),
            'historical': RateLimiter(max_requests=3, time_window=1.0),
            'orders': RateLimiter(max_requests=9, time_window=1.0),
            'default': RateLimiter(max_requests=5, time_window=1.0),
        }
        
        logger.info("Multi-rate limiter initialized with SmartAPI limits")
    
    def acquire(self, endpoint: str = 'default', timeout: Optional[float] = None) -> bool:
        """
        Acquire permission for specific endpoint.
        
        Args:
            endpoint: API endpoint name (login, ltp, historical, orders)
            timeout: Maximum seconds to wait
        
        Returns:
            bool: True if acquired, False if timeout
        """
        limiter = self.limiters.get(endpoint, self.limiters['default'])
        return limiter.acquire(timeout=timeout)
    
    @contextmanager
    def limit(self, endpoint: str = 'default', timeout: Optional[float] = None):
        """
        Context manager for specific endpoint.
        
        Usage:
            with multi_limiter.limit('ltp'):
                response = api.get_ltp()
        """
        if not self.acquire(endpoint=endpoint, timeout=timeout):
            raise TimeoutError(
                f"Rate limiter timeout for endpoint: {endpoint}"
            )
        try:
            yield
        finally:
            pass
    
    def add_limiter(self, name: str, max_requests: int, time_window: float) -> None:
        """
        Add a custom rate limiter.
        
        Args:
            name: Name for the limiter
            max_requests: Max requests in time window
            time_window: Time window in seconds
        """
        self.limiters[name] = RateLimiter(max_requests, time_window)
        logger.debug(f"Added rate limiter: {name}")
    
    def get_status(self) -> dict:
        """
        Get status of all rate limiters.
        
        Returns:
            dict: Status information for each limiter
        """
        status = {}
        for name, limiter in self.limiters.items():
            status[name] = {
                'max_requests': limiter.max_requests,
                'time_window': limiter.time_window,
                'available_tokens': limiter.get_available_tokens(),
                'wait_time': limiter.wait_time_for_token(),
            }
        return status


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("Rate Limiter Test")
    print("=" * 60)
    
    # Test basic rate limiter
    print("\n1. Testing basic rate limiter (5 requests/second)...")
    limiter = RateLimiter(max_requests=5, time_window=1.0)
    
    start = time.time()
    for i in range(10):
        with limiter:
            elapsed = time.time() - start
            print(f"  Request {i+1} at {elapsed:.3f}s - Available: {limiter.get_available_tokens():.2f}")
    
    print(f"✓ Completed 10 requests in {time.time() - start:.3f}s")
    
    # Test multi-rate limiter
    print("\n2. Testing multi-rate limiter...")
    multi = MultiRateLimiter()
    
    # Test LTP endpoint (10/sec)
    print("  Testing LTP endpoint (10 requests/second)...")
    start = time.time()
    for i in range(5):
        with multi.limit('ltp'):
            print(f"    LTP request {i+1}")
    print(f"  ✓ 5 LTP requests in {time.time() - start:.3f}s")
    
    # Show status
    print("\n3. Rate limiter status:")
    status = multi.get_status()
    for endpoint, info in status.items():
        print(f"  {endpoint}:")
        print(f"    Max: {info['max_requests']}/{info['time_window']}s")
        print(f"    Available: {info['available_tokens']:.2f}")
        print(f"    Wait time: {info['wait_time']:.3f}s")
    
    print("\n" + "=" * 60)
    print("✓ Rate limiter working correctly")
    print("=" * 60)
