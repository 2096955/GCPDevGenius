import json
import time
import os
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

class JWTUtils:
    """Utilities for JWT token generation and verification."""
    
    def __init__(self, 
                 jwks_path: Optional[str] = None, 
                 private_key: Optional[bytes] = None, 
                 public_key: Optional[bytes] = None, 
                 key_id: Optional[str] = None,
                 issuer: Optional[str] = None):
        """Initialize JWTUtils with keys.
        
        Args:
            jwks_path: Path to store JWKS file (for server)
            private_key: PEM encoded private key (optional)
            public_key: PEM encoded public key (optional)
            key_id: Key ID for JWK (optional)
            issuer: JWT issuer claim (optional)
        """
        self.jwks_path = jwks_path
        self.private_key = private_key
        self.public_key = public_key
        self.key_id = key_id or str(uuid.uuid4())
        self.issuer = issuer
        
        if not self.private_key or not self.public_key:
            logger.info("Generating new RSA key pair")
            self._generate_keys()
    
    def _generate_keys(self):
        """Generate new RSA key pair."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize private key to PEM
        self.private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key to PEM
        self.public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Save JWKS if path is provided
        if self.jwks_path:
            self.save_jwks()
    
    def _public_key_to_jwk(self) -> Dict[str, Any]:
        """Convert public key to JWK format."""
        # Load public key
        public_key = serialization.load_pem_public_key(self.public_key)
        
        # Get key numbers
        numbers = public_key.public_numbers()
        
        # Encode modulus and exponent
        n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, byteorder='big')
        e = numbers.e.to_bytes(3, byteorder='big')
        
        import base64
        # Create JWK
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.key_id,
            "n": base64.urlsafe_b64encode(n).rstrip(b'=').decode('ascii'),
            "e": base64.urlsafe_b64encode(e).rstrip(b'=').decode('ascii')
        }
        
        return jwk
    
    def save_jwks(self):
        """Save JWKS to file."""
        if not self.jwks_path:
            raise ValueError("JWKS path not provided")
        
        jwks = {
            "keys": [self._public_key_to_jwk()]
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.jwks_path), exist_ok=True)
        
        # Write JWKS to file
        with open(self.jwks_path, 'w') as f:
            json.dump(jwks, f)
        
        logger.info(f"JWKS saved to {self.jwks_path}")
    
    def generate_token(self, 
                      claims: Dict[str, Any], 
                      expiration: Optional[timedelta] = None) -> str:
        """Generate JWT token.
        
        Args:
            claims: Custom claims to include in token
            expiration: Token expiration time (default: 1 hour)
        
        Returns:
            JWT token as string
        """
        if not self.private_key:
            raise ValueError("Private key not available")
        
        # Set default expiration to 1 hour
        if expiration is None:
            expiration = timedelta(hours=1)
        
        # Current time
        now = datetime.utcnow()
        
        # Add standard claims
        token_claims = {
            "iat": int(now.timestamp()),
            "exp": int((now + expiration).timestamp()),
            "jti": str(uuid.uuid4())
        }
        
        # Add issuer if provided
        if self.issuer:
            token_claims["iss"] = self.issuer
        
        # Add custom claims
        token_claims.update(claims)
        
        # Generate token
        token = jwt.encode(
            token_claims,
            self.private_key,
            algorithm="RS256",
            headers={"kid": self.key_id}
        )
        
        return token
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify JWT token.
        
        Args:
            token: JWT token to verify
        
        Returns:
            Tuple of (is_valid, claims)
        """
        if not self.public_key:
            raise ValueError("Public key not available")
        
        try:
            # Decode and verify token
            claims = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                options={"verify_signature": True}
            )
            
            return True, claims
        except jwt.PyJWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return False, None

def create_jwks_endpoint(key_utils: JWTUtils):
    """Create a JWKS endpoint handler for Starlette server.
    
    Args:
        key_utils: JWTUtils instance
    
    Returns:
        Async function to handle JWKS endpoint requests
    """
    from starlette.responses import JSONResponse
    
    async def jwks_endpoint(request):
        """Handle JWKS endpoint request."""
        jwk = key_utils._public_key_to_jwk()
        return JSONResponse({"keys": [jwk]})
    
    return jwks_endpoint 