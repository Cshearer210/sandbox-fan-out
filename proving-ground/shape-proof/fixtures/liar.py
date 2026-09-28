"""This module explains why os.remove, requests and ffmpeg are banned in a checker."""
# never call shutil.rmtree here, and never import PIL
print('the PreToolUse chain refused this')
