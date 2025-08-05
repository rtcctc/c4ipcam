from setuptools import setup, find_packages

def readme():
  with open('README.md', 'r', encoding='utf-8') as f:
    return f.read()

setup(
  name='c4ipcam',
  version='0.0.1',
  author='4edbark',
  author_email='vangogprogprog@gmail.com',
  description='This is a simple module to connect a device with a camera and a device with an OpenCV application.',
  long_description=readme(),
  long_description_content_type='text/markdown',
  url='https://github.com/rtcctc/c4ipcam',
  packages=find_packages(),
  install_requires=['opencv-python>=4.11.0.86'],
  classifiers=[
    'Programming Language :: Python :: 3.11',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent'
  ],
  keywords='',
  project_urls={
    'GitHub': 'https://github.com/rtcctc/c4ipcam'
  },
  entry_points={
        'console_scripts': [
            'c4ipcam = c4ipcam.server:run_server_cli'
        ]
    },
  python_requires='>=3.6'
)