from setuptools import setup, find_packages
import os

version = '1.0'

setup(name='tud.addons.chat',
      version=version,
      description="This addon provides time-controlled chats with moderation possibilities",
      long_description=open("README.md").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        ],
      keywords='',
      author='',
      author_email='',
      url='ssh://git@tools.mz.tu-dresden.de:7999/webcms2/tud.addons.chat.git',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['tud', 'tud.addons'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'plone.api',
          'raptus.multilanguagefields>=1.1b10',
          'Products.ZMySQLDA',
          'simplejson',
          'collective.beaker',
          'python-dateutil'
          # -*- Extra requirements: -*-
      ],
      extras_require={'test': ['plone.app.robotframework']},
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
