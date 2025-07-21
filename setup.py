from setuptools import setup

APP = ['post_viewcount_checker.py']

# ✅ chromedriver 포함
DATA_FILES = [
    ('resources', ['resources/chromedriver'])
]

OPTIONS = {
    'argv_emulation': False,
    'emulate_shell_environment': True,
    'includes': [
        'datetime', 'pytz', 'unicodedata', 'cmath'
    ],
    'packages': [
        'pandas',
        'openpyxl',
        'numpy',
        'dateutil',
        'selenium',
        'xlsxwriter'  # ✅ 반드시 포함
    ],
    'excludes': ['tkinter'],
    # 'resources': ['resources/chromedriver'],  ← ❌ py2app에서는 무시될 수 있음 (data_files로 충분)
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
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'selenium',
        'pandas',
        'openpyxl',
        'numpy',
        'python-dateutil',
        'XlsxWriter'  # ✅ 여기에도 반드시 필요 (대소문자 관계 없이 OK)
    ]
)
