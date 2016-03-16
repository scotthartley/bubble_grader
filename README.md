# bubble_grader: Interpreting scanned multiple choice files with Python

bubble_grader is a simple Python script that takes a scanned image of a multiple-choice bubble form and returns the raw responses in a format that can be interpreted separate (see the [grade_mc](https://github.com/scotthartley/grade_mc) script, for example). Right now, it's pretty bare bones. It takes one image as input (jpg or tif) along with the number of questions. It returns the raw output as a single line of text. It works well in combinations with some simple command line scripting to handle a series of files.

## Requirements

- Python 3
- [Numpy](http://www.numpy.org)
- [Pillow](https://pypi.python.org/pypi/Pillow/)

## Use

