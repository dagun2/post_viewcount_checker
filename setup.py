from setuptools import setup

APP = ['post_viewcount_checker.py']

OPTIONS = {
    'argv_emulation': False,
    'emulate_shell_environment': True,
    'includes': [],                 # 꼭 필요할 때만 채우세요
    'packages': [                   # 순수 파이썬이 아닌 패키지는 여기로
        'pandas',
        'openpyxl',
        'numpy',
        'selenium',
        'xlsxwriter',
        'dateutil',                 # or python-dateutil (install_requires에 기재)
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
        'selenium>=4.10',     # Selenium Manager 포함
        'pandas',
        'openpyxl',
        'numpy',
        'python-dateutil',
        'xlsxwriter'
    ]
)
