# "lines of code":"4","lines of commented":"0"
import os

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 720  # 30 days
# "lines of code":"4","lines of commented":"0"
