import os
TIMEOUT = int(os.getenv('SYNC_TIMEOUT', '30'))  # reads env, not max_retries
