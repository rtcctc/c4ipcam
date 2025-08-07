from setuptools import setup, find_packages

def readme():
  with open('README.md', 'r', encoding='utf-8') as f:
    return f.read()

setup(
  name='c4ipcam',
  version='0.0.3',
  author='4edbark',
  author_email='vangogprogprog@gmail.com',
  description='Simple IP camera streaming module with authentication and compression for OpenCV applications.',
  long_description=readme(),
  long_description_content_type='text/markdown',
  url='https://github.com/rtcctc/c4ipcam',
  packages=find_packages(),
  install_requires=[
    'opencv-python>=4.11.0.86',
    'numpy>=1.21.0'
  ],
  classifiers=[
    'Programming Language :: Python :: 3.11',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Topic :: Multimedia :: Video :: Capture',
    'Topic :: Software Development :: Libraries :: Python Modules'
  ],
  keywords='opencv, ip camera, streaming, video, computer vision, authentication',
  project_urls={
    'GitHub': 'https://github.com/rtcctc/c4ipcam',
    'Bug Reports': 'https://github.com/rtcctc/c4ipcam/issues',
    'Documentation': 'https://github.com/rtcctc/c4ipcam#readme'
  },
  entry_points={
    'console_scripts': [
      'c4ipcam = c4ipcam.server:run_server_cli'
    ]
  },
  python_requires='>=3.6'
)
