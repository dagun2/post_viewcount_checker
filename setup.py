from setuptools import setup

APP = ['post_viewcount_checker.py']

OPTIONS = {
    'argv_emulation': False,
    'emulate_shell_environment': True,
    'includes': [
        'cmath',        # ← 핵심
        'unicodedata',  # 한글 파일명/경로에 유용
        'encodings'     # 인코딩 테이블 누락 방지
    ],
    'packages': [
        'pandas', 'openpyxl', 'numpy', 'selenium', 'xlsxwriter', 'dateutil'
    ],
    'excludes': ['tkinter'],
    'plist': {
        'CFBundleName': 'PostViewcountChecker',
        'CFBundleDisplayName': 'PostViewcountChecker',
        'CFBundleIdentifier': 'com.midnightaxi.post_viewcount_checker',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSEnvironment': {
            'PYTHONIOENCODING': 'utf-8',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8'
        }
    }
}

setup(
    app=APP,
    name='PostViewcountChecker',
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'selenium>=4.10', 'pandas', 'openpyxl', 'numpy',
        'python-dateutil', 'xlsxwriter'
    ]
)
