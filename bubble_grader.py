#! /usr/bin/env python3
""" bubble_grader. A simple program that interprets scanned
multiple-choice answer sheets.

Arguments:
    filename: A single input file (jpg or tif format) for processing. 
        Scanning works well on photocopier if set to Text/Photo, at
        least 100 dpi.
    num_questions: Number of questions in the file.

"""

import sys
import math
from PIL import Image, ImageDraw
from numpy import mean, polyfit, exp, std
from statistics import mode
from random import randint

# Number of calibration bars along left edge of form.
NUM_CALIB_BARS = 63

Q_PER_COL = 20

# Number of pixels of change before straightening.
STRAIGHTEN_THRESHOLD = 5

# Approximate half-width of a calibration bar, relative to total width.
BAR_HALFWIDTH_REL = 0.0085

# Approximate spacing between calibration bars.
BAR_SPACING = 0.014

# Minimum width (as fraction of total height) of calibration bars.
BAR_MIN_HEIGHT = 0.002

# Darkness change threshold for finding markers scanning vertically.
THRESHOLD = 0.3

# Darkness change threshold for locating the calibration bars when
# scanning from left edge.
THRESHOLD_CALIB = 0.1

# Darkness above which a bubble will be considered filled, regardless of
# distance from next darkest point or other factors.
FILLED_THRESHOLD = 0.27
FILLED_THRESHOLD_UNIQUEID = 0.27

# Darkness below which the hand written box for uniqueID will be assumed
# to be empty.
UNIQUEID_WRITING_THRESHOLD = 0.01

# Number of std dev between darkest bubble and mean of remaining
# bubbles.
TOLERANCE = 3
UNIQUEID_TOLERANCE = 1

# Radii used to define search zone for spot measurements, relative to
# total height/width.
BUBBLE_RADIUS_X = 0.0069
BUBBLE_RADIUS_Y = 0.0054

# Distances used to average out when looking for changes in darkness
# (e.g., on calibration).
TRACE_Y_WIDTH = 3
TRACE_X_WIDTH = 6

# Location of the UniqueID box on the Scantron form.
UNIQUEID_X = 36
UNIQUEID_Y = 7

# Location of the Form Number box on the form.
FORM_X = 37
FORM_Y = 46

# Color used to annotate the output scan files.
MARK_COLOR = "rgb(0,120,255)"

SAVE_SIZE = 1200, 1200

def darkness(rgb):
    """Converts an rgb tuple into a darkness value. Uses a sigmoidal
    curve to enhance the contrast.

    Arguments:
        rgb (tuple): Self-explanatory.

    Returns:
        adjusted (float): A darkness value between 0 (white) and 1 
            (black).

    """
    # Defines center point of sigmoidal function. If x = CENTER, output
    # is 0.5.
    CENTER = 0.25

    # Defines severity of sigmoidal function. Larger = sharper change to
    # the limits of 0 and 1.
    ENHANCEMENT = 20
    
    # Converts RGB values to a raw darkness measure. Only reads the red
    # channel so as to ignore as much of red form as possible.
    raw = 1 - rgb[0]/255

    # Enhances "contrast" by applying sigmoidal curve.
    adjusted = 1 / (1 + exp(-(raw - CENTER) * ENHANCEMENT))

    return adjusted


def read_bubble(img, xpix, ypix):
    """Reads the mean darkness centered on the given coordinates, using
    the BUBBLE_RADIUS constants as the sides of a square.

    Arguments:
        img (Image): the image from which the darkness will be read.
        xpix (int): x location (in pixels) for reading.
        ypix (int): y location (in pixels) for reading.

    Returns:
        mean(intensities) (float): Average darkness (0-1).

    """
    # Determines the dimensions of the box to be read, in pixels.
    half_side_x = int(BUBBLE_RADIUS_X * img.size[0])
    half_side_y = int(BUBBLE_RADIUS_Y * img.size[1])

    intensities = []
    for x in range(xpix - half_side_x, xpix + half_side_x + 1):
        for y in range(ypix - half_side_y, ypix + half_side_y + 1):
            intensities.append(darkness(img.getpixel((x,y))))

    return mean(intensities)


def intensity_difference(img, loc, direction):
    """Determines the difference in intensity between a point and the
    next point over in either the x or y directions. Sums orthogonally
    over the ranges defined in the TRACE_X_WIDTH and TRACE_Y_WIDTH
    parameters.

    Arguments:
        img (Image): The image to use.
        loc (tuple): The base location for the measurement, as an (x,y)
            tuple, x and y in pixels. 
        direction (string): Either "x" or "y", indicated which direction 
            to step.

    """
    if direction == "y":
        I1 = mean([darkness(img.getpixel((loc[0] + j, loc[1]))) \
            for j in range(-TRACE_X_WIDTH, TRACE_X_WIDTH)])
        I2 = mean([darkness(img.getpixel((loc[0] + j, loc[1] + 1))) \
            for j in range(-TRACE_X_WIDTH, TRACE_X_WIDTH)])
    elif direction == "x":
        I1 = mean([darkness(img.getpixel((loc[0], loc[1] + j))) \
            for j in range(-TRACE_Y_WIDTH, TRACE_Y_WIDTH)])
        I2 = mean([darkness(img.getpixel((loc[0] + 1, loc[1] + j))) \
            for j in range(-TRACE_Y_WIDTH, TRACE_Y_WIDTH)])

    return I2 - I1


def trace_y_calib_bars(img, xloc):
    """Traces down along xloc. Determines midpoints of calibration bars.

    Arguments:
        img (Image): The image to be used.
        xloc (int): The location (in pixels) to be scanned down.

    Returns:
        midpoints (list): A list of y coords for the midpoints of the 
            calibration bars.

    """
    midpoints = []
    y = 0
    while y < img.size[1] - 1:
        if intensity_difference(img, (xloc, y), "y") > THRESHOLD:
            y_start = y
            # Jumps forward, in front of calibration bar.
            if (y + round(BAR_SPACING*img.size[1])) < img.size[1]:
                y += round(BAR_SPACING*img.size[1])
            else:
                y = img.size[1]
            # Walks back until other edge is found.
            while -intensity_difference(img, (xloc, y), "y") < THRESHOLD:
                y -= 1
            y_end = y
            if (y_end-y_start)/img.size[1] > BAR_MIN_HEIGHT:
                midpoints.append(int((y_start+y_end)/2))
            y += 1
        else:
            y += 1

    return midpoints


def trace_x_calib_bars(img, yloc):
    """Traces down along yloc. Determines midpoints of calibration bars.

    Arguments:
        img (Image): The image to be used.
        yloc (int): The location (in pixels) to be scanned down.

    Returns:
        midpoints (list): A list of y coords for the midpoints of the 
            calibration bars.

    """
    midpoints = []
    x = 0
    while x < img.size[0] - 1:
        if intensity_difference(img, (x, yloc), "x") > THRESHOLD:
            x_start = x
            x += round(BAR_HALFWIDTH_REL * 3 * img.size[0])
            while -intensity_difference(img, (x, yloc), "x") < THRESHOLD:
                x -= 1
            x_end = x
            midpoints.append(int((x_start+x_end)/2))
            x += 1
        else:
            x += 1

    return midpoints


def sum_y(img, xloc):
    """Determines the average darkness along the entirety of the y axis 
    at xloc.

    Arguments:
        img (Image): The image to be used.
        xloc (integer): The location (pixel) to measure darkness.

    Returns:
        Average darkness along xloc.

    """
    tot = 0
    for y in range(img.size[1]):
        tot += darkness(img.getpixel((xloc, y)))

    return tot / img.size[1]


def find_bars(img):
    """Locates the calibration bars by counting from left edge of pic.
    Uses the total sum along y position.

    Arguments:
        img (Image): The image to be used.

    Returns:
        The midpoint of the calibration bars.

    """
    x = 1
    while sum_y(img, x) < THRESHOLD_CALIB:
        x += 1
    xmin = x
    while sum_y(img, x) > THRESHOLD_CALIB:
        x += 1
    xmax = x

    return round((xmin + xmax) / 2)


def calibrate(scan):
    """Finds the calibration bars on the form and returns the x and y
    grids for locating bubbles.

    Arguments:
        scan (Image): The form.

    Returns:
        x_grid (List): List of x coordinates. x_grid[i] gives the x 
            coordinate, in pixels, of grid location i.
        calib_bars_y (List): Same, but for y coordinates.

    """
    # Locate the x coordinate of the calibration bars down left side of
    # form.
    bar_loc = find_bars(scan)
    # Locate the calibration bars down and to right. Starts with
    # vertical bonds, then uses first of these to locate the horizontal
    # bars.
    calib_bars_y = trace_y_calib_bars(scan, bar_loc)
    calib_bars_x = trace_x_calib_bars(scan, calib_bars_y[0])

    # Draws the found calibration bars on the image, for future
    # debugging purposes.
    draw_on_img = ImageDraw.Draw(scan)
    for bar in calib_bars_y:
        draw_on_img.rectangle([bar_loc - TRACE_X_WIDTH*3, bar+1, 
            bar_loc + TRACE_X_WIDTH*3, bar-1], fill=MARK_COLOR)

    # Outputs an error if the wrong number of calibration bars found.
    if len(calib_bars_y) != NUM_CALIB_BARS:
        print("ERROR: Found {} calibration bars, expected {}.".format(
            len(calib_bars_y), NUM_CALIB_BARS))

    # The horizontal separation between the bubbles is the separation
    # between the calibration bars on the y axis. Determined from the
    # separation between the first and last one.
    bubble_dist = (calib_bars_y[-1] - calib_bars_y[0]) \
                   / (len(calib_bars_y) - 1)

    # Generates the grid along the x axis.
    x_grid = [round(calib_bars_x[1] + i * bubble_dist) 
              for i in range(44)]

    return x_grid, calib_bars_y

def align_img_angle(scan):
    """Determines the angle by which to rotate the image in order to
    straighten it. Uses the location of the calibration
    bars.

    Arguments:
        scan (Image): The image of the form.

    Returns:
        rot_angle (float): The angle (in degrees) by which the image 
            must be rotated to straighten it.

    """
    # Locate the calibration bars x axis.
    bar_loc = find_bars(scan)
    # Locate the y coords of the calibration bars.
    calib_bars_y = trace_y_calib_bars(scan, bar_loc)

    # Identify the x locations of the edges of the calibration bars.
    # These are used to determine the angle of rotation.
    x_locations = []
    for bar in calib_bars_y:
        x = 1
        while not intensity_difference(scan, (x, bar), "x") > THRESHOLD:
            x += 1
        x_locations.append(x)

    # The angle is determined only if the difference between the first
    # and last coordinates is above the straighten threshold. This is
    # necessary because it will rotate by an unreasonable amount if
    # there is little straightening needed but it fits to a distribution
    # of points.
    if abs(x_locations[-1] - x_locations[0]) > STRAIGHTEN_THRESHOLD:
        m, b = polyfit(x_locations, calib_bars_y, 1)
        rot_angle = math.atan(-1/m)/math.pi * 180
    else:
        rot_angle = 0

    return rot_angle


def draw_bubble(img, x_grid, y_grid, x, y):
    """Draws a bubble on the given image at the given location.

    """
    half_side_x = int(BUBBLE_RADIUS_X * img.size[0])
    half_side_y = int(BUBBLE_RADIUS_Y * img.size[1])

    draw_on_img = ImageDraw.Draw(img)
    draw_on_img.rectangle([x_grid[x] - half_side_x, y_grid[y] + 
                           half_side_y, x_grid[x] + 
                           half_side_x, y_grid[y] + 
                           half_side_y + 2], fill=MARK_COLOR)
    draw_on_img.rectangle([x_grid[x] - half_side_x, y_grid[y] - 
                           half_side_y, x_grid[x] + 
                           half_side_x, y_grid[y] - 
                           half_side_y - 2], fill=MARK_COLOR)
    draw_on_img.rectangle([x_grid[x] + half_side_x, y_grid[y] - 
                           half_side_y, x_grid[x] + 
                           half_side_x + 2, y_grid[y] + 
                           half_side_y], fill=MARK_COLOR)
    draw_on_img.rectangle([x_grid[x] - half_side_x, y_grid[y] + 
                           half_side_y, x_grid[x] - 
                           half_side_x - 2, y_grid[y] - 
                           half_side_y], fill=MARK_COLOR)


def get_uniqueid(scan, x_grid, y_grid):
    """Reads the student's ID from the form.

    """
    uniqueid = []
    for char_num in range(8):
        bubble_intensities = [read_bubble(scan, 
                              x_grid[UNIQUEID_X+char_num], 
                              y_grid[UNIQUEID_Y+y]) for y in range(36)]

        choice = bubble_intensities.index(max(bubble_intensities))

        bub_sort = sorted(bubble_intensities)
        num_std = ( bub_sort[-1] - mean(bub_sort[:-1]) ) / \
                    std(bub_sort[:-1])

        if num_std < UNIQUEID_TOLERANCE or ( 
                read_bubble(scan, x_grid[UNIQUEID_X+char_num], 
                    y_grid[UNIQUEID_Y-1]) < UNIQUEID_WRITING_THRESHOLD 
                    and bub_sort[-1] < FILLED_THRESHOLD_UNIQUEID ):
            uniqueid.append(" ")
        elif choice > 25:
            uniqueid.append(chr(choice - 26 + ord("0")))
            draw_bubble(scan, x_grid, y_grid, UNIQUEID_X + char_num, 
                UNIQUEID_Y + choice)
        else:
            uniqueid.append(chr(choice + ord("A")))
            draw_bubble(scan, x_grid, y_grid, UNIQUEID_X + char_num, 
                UNIQUEID_Y + choice)

    return uniqueid


def grade_5choice(scan, x_grid, y_grid, startx, starty):
    """Grades a 5-choice MC question.


    """
    bubble_intensities = [read_bubble(scan, x_grid[x], y_grid[starty]) \
        for x in range(startx, startx + 5)]

    choice = bubble_intensities.index(max(bubble_intensities))

    bub_sort = sorted(bubble_intensities)
    num_std = ( bub_sort[-1] - mean(bub_sort[:-1]) ) / std(bub_sort[:-1])

    # print(num_std) # Useful for calibrating TOLERANCE

    if num_std < TOLERANCE or bub_sort[-1] < FILLED_THRESHOLD:
        return "."
    else:
        draw_bubble(scan, x_grid, y_grid, startx + choice, starty)
        return choice


def get_form_num(scan, x_grid, y_grid):
    """Reads the form number.

    """
    bubble_intensities = [read_bubble(scan, x_grid[x], y_grid[FORM_Y]) 
        for x in range(FORM_X, FORM_X + 8, 2)]

    choice = bubble_intensities.index(max(bubble_intensities))
    bub_sort = sorted(bubble_intensities)
    num_std = ( bub_sort[-1] - bub_sort[-2] ) / std(bub_sort[:-1])

    if num_std < TOLERANCE:
        return "."
    else:
        draw_bubble(scan, x_grid, y_grid, FORM_X + choice*2, FORM_Y)
        return choice % 2 + 1


def read_scan(filename, num_questions):
    with Image.open(filename) as scan:
        scan_conv = scan.convert('RGBA')
        rot_angle = align_img_angle(scan_conv)
        scan_rot = scan_conv.rotate(rot_angle, expand=1)
        scan_white = Image.new('RGBA', scan_rot.size, (255,)*4)
        scan_fix = Image.composite(scan_rot, scan_white, scan_rot)

        x_grid, y_grid = calibrate(scan_fix)

        uniqueid = "".join(get_uniqueid(scan_fix, x_grid, y_grid))
        if len(uniqueid) == 0:
            uniqueid = "blank{}".format(randint(0,99))

        form = get_form_num(scan_fix, x_grid, y_grid)
        
        answers_list = []
        for column in range(((num_questions - 1) // Q_PER_COL) + 1):
            if (column + 1)*Q_PER_COL <= num_questions:
                max_row = Q_PER_COL
            else:
                max_row = num_questions % Q_PER_COL

            for row in range(max_row):
                answers_list.append(str(grade_5choice(scan_fix, x_grid, 
                    y_grid, 2 + 9*column, 23 + 2*row)))

        q_answers = "".join(answers_list)

        print("{} {}{}".format(uniqueid, form, q_answers))

        scan_tosave = scan_fix.copy()
        scan_tosave.thumbnail(SAVE_SIZE)
        scan_tosave.save('{}.jpg'.format("".join(uniqueid).strip()))


if __name__ == '__main__':
    read_scan(sys.argv[1], int(sys.argv[2]))

