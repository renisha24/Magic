from base64 import b64encode
from os import makedirs
from os.path import join, basename
from sys import argv
from flask import Flask, request, redirect, url_for, send_from_directory, get_template_attribute, flash
from werkzeug.utils import secure_filename
from flask import render_template
from collections import defaultdict

import json
import requests
import os
import datefinder
import re
import xlsxwriter
import glob2
import time
import shutil



ENDPOINT_URL = 'https://vision.googleapis.com/v1/images:annotate'
RESULTS_DIR = 'jsons'
UPLOAD_DIR = 'uploads'
makedirs(RESULTS_DIR, exist_ok=True)
makedirs(UPLOAD_DIR, exist_ok=True)
alldone= False
global userfilenames
global filenames
userfilenames = []
filenames = []
# Initialize the Flask application
app = Flask(__name__)

# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = 'uploads/'

# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set([ 'pdf', 'png', 'jpg', 'jpeg'])


# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


# This route will show a form to perform an AJAX request
# jQuery is loaded to execute the request and update the
# value of the operation
@app.route('/')
def index():
    return render_template('index.html')


# Route that will process the file upload
@app.route('/upload', methods=['POST'])

def upload():
    # Get the name of the uploaded file
    uploaded_files = request.files.getlist("file[]")
    totalfiles=len(glob2.glob(app.config['UPLOAD_FOLDER']+'*'))
    #if totalfiles==0:
     #   userfilenames=[]
      #  filenames=[]
    print("tell me the num of totalfiles" +str(totalfiles))

    for index, file in enumerate(uploaded_files):
        # Check if the file is one of the allowed types/extensions
        if file and allowed_file(file.filename):
            userfilenames.append(secure_filename(file.filename))
            # Make the filename safe, remove unsupported chars
            file_extension = os.path.splitext(file.filename)[1]
            filename = str(index+totalfiles)+str(file_extension)
            print("tell me the filename" + filename + " index "+str(index)+" totalfiles "+str(totalfiles))
            # Move the filetotalfiles form the temporal folder to the upload
            # folder we setup
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Save the filename into a list, we'll use it later
            filenames.append(app.config['UPLOAD_FOLDER']+filename)

            # Redirect the user to the uploaded_file route, which
            # will basicaly show on the browser the uploaded file
            # Load an html page with a link to each uploaded file

    return render_template("index.html", filenames=userfilenames)



# Route that will process the uploaded files
@app.route('/process', methods=['POST'])
def process():
    try:
        processfile()
        print("done")
        return render_template('index.html', processed=True);
    except:
        return render_template('index.html', error=True);
    finally:
        userfilenames = []
        filenames = []





def processfile():
    #api_key='123'
    image_filenames =[]
    pdf_filenames=[]
    d = defaultdict(list)
    i = 1
    for file in filenames:
        if os.path.splitext(file)[1]=='.pdf':
            pdf_filenames.append(file)
        else:
            image_filenames.append(file)
    if(image_filenames):
        processImage(image_filenames,d,i)
    if(pdf_filenames):
        processPdf(pdf_filenames,d,i)
    if d:
        writeToExcel(d)
        zipContent()


def processImage(image_filenames,d,i):
        #api_key = 'AIzaSyCrOfaHEfR1yN7G5DTlGg4OsBgI_6viz-s'
        api_key = '1234'
        response = request_ocr(api_key, image_filenames)
        if response.status_code != 200 or response.json().get('error'):
            print(response.text)
        else:
            for idx, resp in enumerate(response.json()['responses']):
                # save to JSON file
                imgname = image_filenames[idx]
                jpath = join(RESULTS_DIR, basename(imgname) + '.json')
                with open(jpath, 'w') as f:
                    datatxt = json.dumps(resp, indent=2)
                    print("Wrote", len(datatxt), "bytes to", jpath)
                    f.write(datatxt)

                # print the plaintext to screen for convenience
                print("---------------------------------------------")
                t = resp['textAnnotations'][0]
                #print("    Bounding Polygon:")
                #print(t['boundingPoly'])
                #print("    Text:")
                print(t['description'])
                desc = t['description']
                # for date
                matches = list(datefinder.find_dates(t['description']))
                pattern = re.findall(r'([£$€$R])[\s]?(\d+(?:\.\d{2})?)', desc)
                if 'OOLA' in desc:
                    d[i].append('taxi')
                    d[i].append('OOLA')
                    d[i].append(str(matches[0].date()))
                    if 'R' in pattern[0][0]:
                        d[i].append('INR')
                        d[i].append(pattern[0][1])
                    elif '$' in pattern[0][0]:
                        d[i].append('USD')
                        d[i].append(pattern[0][1])
                    elif '€' in pattern[0][0]:
                        d[i].append('USD')
                        d[i].append(pattern[0][1])
                elif 'UBER' in desc:
                    d[i].append('taxi')
                    d[i].append('UBER')
                    d[i].append(str(matches[1].date()))
                    if 'R' in pattern[0][0]:
                        d[i].append('INR')
                        d[i].append(pattern[0][1])
                    elif '$' in pattern[0][0]:
                        d[i].append('USD')
                        d[i].append(pattern[0][1])
                    elif '€' in pattern[0][0]:
                        d[i].append('USD')
                        d[i].append(pattern[0][1])
                i += 1
            print(d)

def processPdf(pdf_filenames,d,i):
    pass


def writeToExcel(d):
    workbook = xlsxwriter.Workbook('new.xlsx')
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, 'SL. No')
    worksheet.write(0, 1, 'Expense Medium')
    worksheet.write(0, 2, 'Medium Name')
    worksheet.write(0, 3, 'Date')
    worksheet.write(0, 4, 'Currency')
    worksheet.write(0, 5, 'Currency Value')
    worksheet.write(0, 6, 'Image')

    row = 1
    list_of_uploads = glob2.glob('output/'+'*')
    img_no = 0
    for key in d.keys():
        worksheet.write(row, 0, key)
        worksheet.write_row(row, 1, d[key])
        worksheet.write_url(row, 6, r'' + list_of_uploads[img_no] + '')
        row += 1
        img_no += 1
    workbook.close()

def zipContent():
    st = int(time.time())
    new_file = "EX_" + str(st)

    if not os.path.exists('root'):
        os.makedirs('root')

    if not os.path.exists(new_file):
        os.makedirs(new_file)

    shutil.copy('new.xlsx', new_file)

    def copytree(src, dst, symlinks=False, ignore=None):
        if not os.path.exists(new_file + '\\output'):
            os.makedirs(new_file + '\\output')
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)

    copytree(app.config['UPLOAD_FOLDER'], new_file + '\\output')

    shutil.make_archive("root\\" + new_file, "zip", new_file)

    shutil.rmtree(new_file)
    shutil.rmtree(app.config['UPLOAD_FOLDER'])
    shutil.rmtree('new.xlsx')



def make_image_data_list(image_filenames):
    """
    image_filenames is a list of filename strings
    Returns a list of dicts formatted as the Vision API
        needs them to be
    """
    img_requests = []
    for imgname in image_filenames:
        with open(imgname, 'rb') as f:
            ctxt = b64encode(f.read()).decode()
            img_requests.append({
                'image': {'content': ctxt},
                'features': [{
                    'type': 'TEXT_DETECTION',
                    'maxResults': 1
                }]
            })
    return img_requests


def make_image_data(image_filenames):
    """Returns the image data lists as bytes"""
    imgdict = make_image_data_list(image_filenames)
    return json.dumps({"requests": imgdict}).encode()


def request_ocr(api_key, image_filenames):
    response = requests.post(ENDPOINT_URL,
                             data=make_image_data(image_filenames),
                             params={'key': api_key},
                             headers={'Content-Type': 'application/json'})
    return response


if __name__ == '__main__':

    app.run(

    )
