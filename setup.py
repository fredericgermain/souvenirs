from setuptools import setup

setup(name='souvenirs',
      version='0.1',
      description='locally manage private media files',
      url='http://github.com/fredericgermain/souvenirs',
      author='Frederic Germain',
      author_email='frederic.germain@gmail.com',
      license='GPLv2',
      packages=['souvenirs'],
      install_requires=[
          'kaa-metadata',
      ],
      zip_safe=False)

