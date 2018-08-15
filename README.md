# bubble_grader: Interpreting scanned multiple choice files with Python

bubble_grader is a Python 3 script that takes a scanned image of a multiple-choice bubble form and returns the raw responses in a format that can be interpreted separately (see the [grade_mc](https://github.com/scotthartley/grade_mc) script, for example). Right now, it's pretty bare bones. It takes one image as input (jpg or tif) along with the number of questions. It returns the raw output as a single line of text. It works well in combination with some simple command line scripting to handle a series of files.

## Requirements

- Python 3
- [Numpy](http://www.numpy.org)
- [Pillow](https://pypi.python.org/pypi/Pillow/)

## Installation

Install via setup.py or through the dist.

## Use

As long as the script is executable, it's simply a matter of passing the filename of the image to be analyzed followed by the number of questions as command-line arguments. The output of the program is a list of responses (to stdout), and a jpg image of the scanned form labeled with the ID of the student and with the recognized bubbles highlighted. This makes it easier to check for errors (which do occasionally occur if the markings are too faint or there are extraneous marks on the paper).

The script as presented is set up to handle the standard forms used at Miami University (Ohio). It should be possible to adjust the (many) parameters to accommodate other form layouts, but this will, in all honesty, take some work.