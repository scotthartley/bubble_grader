from setuptools import setup


def readme():
    with open("README.rst") as file:
        return file.read()


setup(name="bubble_grader",
      version=1.0,
      description=("Grade scanned MC exam sheets."),
      long_description=readme(),
      author="Scott Hartley",
      author_email="scott.hartley@miamioh.edu",
      url="https://hartleygroup.org",
      license="MIT",
      packages=["bubble_grader"],
      entry_points={
          'console_scripts': [
              'bubble_grader = bubble_grader:main'
          ]
      },
      install_requires=["Pillow", "numpy"],
      python_requires=">=3",
      )
