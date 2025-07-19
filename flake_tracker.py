import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import os
import gspread
import requests
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# These global variables store the values for the Flake Tracker main screen inputs
horizontal_max = "0"
vertical_max = "0"
down_from_TR = "0"
left_from_TR = "0"
approx_num_layers = "0"
image_1_path = ""
image_2_path = ""

# This variable is where the extracted flake_id is stored
flake_id = "0"

# Define the scope (this contains the authorization for the APIs we used)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']

# These variables store the JSON information as well as the access information for the specific slides & sheets we want to edit (gathered from options screen & json input)
json = ""
creds = ""
client = ""
presentation_id = ""
sheet = ""
slides_service = ""
drive_service = ""
pres_id_dict = {}

# 🔒 Global configuration for github upload
github_token = ""
github_repo = ""
github_branch = ""
github_upload_path = ""

def load_in_env_information(filename):
    load_dotenv(filename) # <--- load in our .env file
    global github_token, github_repo, github_branch, github_upload_path, json

    # Now you can use os.getenv to access them
    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPO")
    github_branch = os.getenv("GITHUB_BRANCH")
    github_upload_path = os.getenv("GITHUB_UPLOAD_PATH")
    json = os.getenv("JSON")


def process_presentation_IDs(spreadsheet_name, sheet_name):
    """This method takes in a spreadsheet name and sheet name assuming it contains the two columns 'Slideshow_Name' and
       'Presentation_ID' and processes the sheet into a dict with keys of the slideshow name and values of the
       presentation ID to make processing in plain english easier.

    Args:
        spreadsheet_name (str): The name of the spreadsheet containing our information.
        sheet_name (str): The name of the sheet within our spreadsheet containing our information.

    Returns:
        dict: A dict with keys of the slideshow name and values of the presentation ID
    """
    pres_id_sheet = client.open(spreadsheet_name).worksheet(sheet_name)
    records = pres_id_sheet.get_all_records()
    dict_to_return = {}
    for item in records:
        dict_to_return[item['Slideshow_Name']] = item['Presentation_ID']
    return dict_to_return


def load_options(f_name):
    """ This method takes in a file name that should store dropdown options (1 per line) and returns a 
        list of options to be passed into a dropdown widget. If the file does not exist then it returns
        an empty list.
    Args:
        f_name (str): The name of the file that we want to read options from

    Returns:
        list: A list of options corresponding to each new line in the passed in file (if file cannot be 
              found, returns an empty list).
    """
    if not os.path.exists(f_name): # <--- check if we can find a file with that name in the same directory as the program is being run from
        return [] # <--- Returning empty list
    # Note that the above if statement guarantees that if the file does not exist we do not try to open it. If we try to open a file in read mode without it existing, it will return an error.
    with open(f_name, "r") as f: # <--- open a file with the given file name in reading mode (we are not planning to modify the file)
        return [line.strip() for line in f.readlines() if line.strip()] # <--- Lambda function that iterates through existing lines of a file and then, if removing leading and trailing whitespace doesn't result in an empty string, appends that line as a list element


def save_option(option, f_name):
    """Saves a new line into the given file (used to store new dropdown inputs for the next time the program is opened)

    Args:
        option (str): dropdown option to save on a new line
        f_name (str): name of the file to store the option in
    """
    with open(f_name, "a") as f: # <--- open the file with the given name
        f.write(option + "\n") # <--- write in the option and start a new line after


def get_dropdown_value(dropdown, f_name):
    """A method that takes in a reference to a Tkinter ComboBox and a filename, gets the current value that the 
       ComboBox (dropdown) is set to, adds that to a file if it is not currently a saved value, and then returns 
       the value.

    Args:
        dropdown (TKinter ComboBox): A reference to a dropdown input displayed on the screen
        f_name (str): Filename that is connected to saved dropdown options

    Returns:
        str: The value currently stored in the dropdown's input box
    """
    input_value = dropdown.get().strip() # <--- gets the dropdown input and removes any surrounding whitespace
    if input_value and input_value not in dropdown['values']: # <--- if the input_value isn't empty and we don't already have it stored
        current_values = list(dropdown['values']) # <--- get the current list of values the dropdown is storing
        current_values.append(input_value) # <--- append our new value to the list
        dropdown['values'] = current_values # <--- update the list of values to the appended version of the list
        # The reason we can't just add to dropdown['values'] like dropdown['values'].append(input_value) is because 
        # it is a tuple and tuples are immutable. (Casting it to a list would just create a new list, it doesn't change
        # the actual dropdown options).
        save_option(input_value, f_name) # <--- Call our method to add the new option to the file that stores all of our options for this dropdown
    return input_value

def get_presentation_ID_from_slideshow_name(slideshow_name):
    """Returns the presentation ID given the slideshow name.

    Args:
        slideshow_name (str): The name of the slideshow we want an ID for.

    Returns:
        str: The presentation ID.
    """
    return pres_id_dict[slideshow_name]


def load_settings_from_inputs(pres_id, spreadsheet_name, sheet_name):
    """A method to set global variables for google APIs access. Opens up slideshow and spreadsheet according to input.

    Args:
        pres_id (str): The ID found in the URL for a given google slide (make sure that the slide in question has been 
                       shared with the service account email)
        spreadsheet_name (str): The name of the spreadsheet you want to edit (make sure that it is shared with the 
                                service account email)
        sheet_name (str): The name of the sheet within the spreadsheet that you want to edit
    """
    global presentation_id, sheet # <--- make sure we are setting the global variables
    
    presentation_id = pres_id
    sheet = client.open(spreadsheet_name).worksheet(sheet_name)

def setup_env_info():
    """"A method to set global variables for google APIs access and GitHub access. Connects to drive after setting up 
        JSON service account.
    """
    global creds, client, slides_service, drive_service, json
    env_filename = get_dropdown_value(env_select, "env_filenames.txt") # <--- get .env filename from dropdown
    # Set up service account
    load_in_env_information(env_filename)
    creds = Credentials.from_service_account_file(json, scopes=SCOPES) 
    client = gspread.authorize(creds)
    slides_service = build('slides', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    env_selector_root.destroy() # <--- destroy selector page


def shutdown_options_screen():
    """
        Get all of the options screen input values, pass them into the method to load settings and access to the 
        relevant sheets/slides. Then shut down the options window.
    """
    # Get all of the dropdown values
    slideshow_name = get_dropdown_value(presentation_id_select, "presentation_ids.txt")
    spreadsheet = get_dropdown_value(spreadsheet_select, "spreadsheets.txt")
    sheet = get_dropdown_value(sheet_select, "sheets.txt")

    load_settings_from_inputs(get_presentation_ID_from_slideshow_name(slideshow_name), spreadsheet, sheet) # <--- Load settings

    options_root.destroy() # <--- Close window

def upload_image_to_github(image_path):
    """
    Uploads an image to a public GitHub repo and returns a raw URL to access it

    Args:
        image_path (str): Local path to the image that we want to upload

    Returns:
        str: Public raw.githubusercontent.com URL
    """
    global github_repo, github_branch, github_token, github_upload_path
    filename = os.path.basename(image_path) # <--- get the filename from the image path
    name, ext = os.path.splitext(filename) # <--- split the name of the file and the file extension (e.g. ".png" or ".jpg")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S") # <--- get the timestamp to make this filename unique
    unique_filename = f"{name}_{timestamp}{ext}" # <--- combine our extracted information to get a fully unique filename

    github_api_url = f"https://api.github.com/repos/{github_repo}/contents/{github_upload_path}/{unique_filename}" # <--- format the github api url

    # Encode the image to upload
    with open(image_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # Create upload request information
    headers = {
        "Authorization": f"token {github_token}", # <--- what's the personal access github token we're using?
        "Accept": "application/vnd.github+json"
    }
    data = {
        "message": f"Upload {unique_filename}", # <--- what's the filename of our upload?
        "content": content, # <--- what's our encoded image?
        "branch": github_branch # <--- what branch of our repo are we uploading to?
    }

    response = requests.put(github_api_url, headers=headers, json=data) # <--- submit upload request


    if response.status_code == 201: # <--- if the upload goes well
        # Return raw.githubusercontent URL
        raw_url = f"https://raw.githubusercontent.com/{github_repo}/{github_branch}/{github_upload_path}/{unique_filename}"
        return raw_url
    else: # <--- if something went wrong with the upload
        raise Exception(f"GitHub upload failed: {response.status_code} {response.json()}")

def create_add_image_to_slide_request(image_url, slide_id, height, width, x_pos, y_pos, x_scale, y_scale):
    """ Creates a request dictionary to add a given image onto a given slide with the given specifications.

    Args:
        image_url (str): The google drive public URL linking to the image to add 
        slide_id (str): The ID for the slide we want to place the images on
        height (float): The height of the image
        width (float): The width of the image
        x_pos (float): Where on the screen we want it to be in the x-direction (The origin is the top left corner)
        y_pos (float): Where on the screen we want it to be in the y-direction (The origin is the top left corner)
        x_scale (float): How we want to scale the image in the x-direction
        y_scale (float): How we want to scale the image in the y-direction

    Returns:
        dict: A request dictionary that details how we want to place the image on the slide with the given specifications.
    """
    request = {
            "createImage": {
                "url": image_url, # <--- pass in image URL
                "elementProperties": {
                    "pageObjectId": slide_id, # <--- pass in slide ID
                    "size": {
                        "height": {"magnitude": height, "unit": "EMU"}, # <--- pass in image height
                        "width": {"magnitude": width, "unit": "EMU"} # <--- pass in image width
                    },
                    "transform": {
                        "scaleX": x_scale, # <--- pass in image x-scale
                        "scaleY": y_scale, # <--- pass in image y-scale
                        "translateX": x_pos, # <--- pass in image x-position
                        "translateY": y_pos, # <--- pass in image y-position
                        "unit": "EMU" # <--- specify the units for the above transformations (scale and translation)
                    }
                }
            }
        }
    return request

def add_images_to_slide(image_1_url, image_2_url, slide_id):
    """Places two images on a given slide around the middle of the screen side by side so that they fill the slide horizontally.

    Args:
        image_1_url (str): The google drive public URL linking to the first image to add (will be on the left)
        image_2_url (str): The google drive public URL linking to the second image to add (will be on the right)
        slide_id (str): The ID for the slide we want to place the images on
    """
    requests = []
    requests.append(create_add_image_to_slide_request(image_1_url, slide_id, 3000000, 4000000, 23000, 600000, 1.14, 1.13)) # <--- add request to place image_1 on slide to request list
    requests.append(create_add_image_to_slide_request(image_2_url, slide_id, 3000000, 4000000, 4555000, 600000, 1.14, 1.13)) # <--- add request to place image_2 on slide to request list
    slides_service.presentations().batchUpdate(presentationId=presentation_id, body={"requests": requests}).execute() # <--- do a batch update on the presentation with all of the requests on the request list

def duplicate_template_slide():
    """Creates and submits a request to duplicate the first slide in the globally defined presentation

    Returns:
        str: The ID for the new slide that was just duplicated
    """
    global presentation_id # <--- Make sure we are using the global presentation_id
    response = slides_service.presentations().get(presentationId=presentation_id).execute() # <--- Get the presentation we want to access
    slides = response['slides'] # <--- Access the dict of info for each slide in the presentation
    template_slide_id = slides[0]['objectId'] # <--- Since we are using the first slide in the presentation as our template, we want the ID of THAT SPECIFIC SLIDE
   
   # Call an update where we request to duplicate the template slide
    duplicate_response = slides_service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={
            "requests": [
                {
                    "duplicateObject": {
                        "objectId": template_slide_id
                    }
                }
            ]
        }
    ).execute()

    new_slide_id = duplicate_response['replies'][0]['duplicateObject']['objectId'] # <--- Get the slide ID of the newly duplicated slide 
    return new_slide_id

def move_slide(slide_id, new_slide_index):
    """A method to move a certain slide in our slideshow to a new position

    Args:
        slide_id (str): The ID of the slide to move 
        last_slide_index (int): The new index to move the side to do
    """
    requests = []
    move_request = {
        "updateSlidesPosition": {
            "slideObjectIds": [slide_id], # <--- the slide we want to move
            "insertionIndex": new_slide_index # <--- the position to move to
        }
    }
    requests.append(move_request) # <--- add this move_request to our list of requests
    slides_service.presentations().batchUpdate(presentationId=presentation_id, body={"requests": requests}).execute() # <--- send our request out to actually update the presentation


def create_replace_text_requests(slide_id, old_text, new_text):
    """ Method to format a request to replace the text on a given slide. 

    Args:
        slide_id (str): The ID of the slide to move 
        old_text (str): The text that we want to replace
        new_text (str): The text that we want to replace with

    Returns:
        dict: A request dictionary that details how we want to replace the text on a given slide
    """
    request = {
        "replaceAllText": {
            "containsText": {
                "text": old_text,
                "matchCase": True
            },
            "replaceText": new_text,
            "pageObjectIds": [slide_id]
        }
    }
    return request

def fill_text(new_slide_id, flake_id, size, nav_instr):
    """ Method to replace all template text on a slide with our stored information.
    Args:
        new_slide_id (str): The slide to place our information on
        flake_id (str): The flake_id string
        size (str): The size description string
        nav_instr (str): The navigation description string
    """
    requests = []

    requests.append(create_replace_text_requests(new_slide_id, "{{FlakeID}}", flake_id)) # <--- create request to replace flake_id template text
    requests.append(create_replace_text_requests(new_slide_id, "{{MaxDimensions}}", size)) # <--- create request to replace dimensions template text
    requests.append(create_replace_text_requests(new_slide_id, "{{Navigation}}", nav_instr)) # <--- create request to replace navigation template text

    slides_service.presentations().batchUpdate(presentationId=presentation_id, body={"requests": requests}).execute() # <--- submit all requests to update slide

def format_navigation_string(down_from_TR, left_from_TR):
    """ A method to format the navigation string and handle edge cases of values for the down_from_TR and left_from_TR values.

    Args:
        down_from_TR (float): A float describing how many screens down from the top right a given flake is
        left_from_TR (float): A float describing how many screens left from the top right a given flake is

    Returns:
        str: A string that contains the navigation instructions from the top right in plain english.
    """
    #Set up our instruction default strings
    down_part = f"Down {down_from_TR} Frames"
    left_part = f"Left {left_from_TR} Frames"
    if down_from_TR == 0 and left_from_TR == 0: # <--- handle case where the flake is at the top right
        return "Flake is at Top Right"
    if down_from_TR == 1: # <--- if our value is one, make sure we say "Frame" at the end instead of "Frames"
        down_part = f"Down {down_from_TR} Frame"
    if left_from_TR == 1: # <--- if our value is one, make sure we say "Frame" at the end instead of "Frames"
        left_part = f"Left {left_from_TR} Frame"
    if left_from_TR == 0: # <--- if our value is zero for left_from_TR, only return the down_part navigation instructions
        return down_part
    if down_from_TR == 0: # <--- if our value is zero for down_from_TR, only return the left_part navigation instructions
        return left_part
    return f"{down_part} and {left_part}" # <--- base case where our string just consists of the default options set at the beginning

def parse_flake_id(flake_id):
    """ Parses a flake ID string in the format 'S<chip_num>_<flake_num>_<MMDDYY>' and returns chip_num, flake_num, and 
        a formatted date string (MM/DD/YYYY).

    Args:
        flake_id (str): Flake identifier string (e.g., 'S2_1_052825')

    Raises:
        ValueError: If the string is not formatted as the above example is, then the method will raise an exception

    Returns:
        dict: A dictionary containing the extracted chip number, flake number, and date
    """
    try:
        parts = flake_id.split('_') # <--- split the flake_id string where there are underscore characters ('-') (e.g. 'S2_1_052825' --> ['S2', '1', '052825'])
        chip_num = int(parts[0][1:]) # <--- remove the 'S' prefix from the first list item (chip number) and cast the remaining character to an int
        flake_num = int(parts[1]) # <--- take the second list item (flake number) and cast it to an int
        date_raw = parts[2] # <--- get the string representing the date from the third list item
        date = f"{date_raw[:2]}/{date_raw[2:4]}/20{date_raw[4:]}" # <--- process this string to have the format MM/DD/YYYY
        return {
            'chip_num': chip_num,
            'flake_num': flake_num,
            'date': date
        }
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid sample ID format: '{flake_id}'") from e # <--- raise error for invalid formatted input


def get_flake_id_from_filepath(filepath):
    """_summary_

    Args:
        filepath (str): The path to our file to extract information from

    Returns:
        str: A flake id in the following format SC_F_MMDDYY (C = chip number, F = flake number, MMDDYY = date)
    """
    folder_name = os.path.basename(os.path.dirname(filepath)) # <--- This will extract the folder name our image is in (this should be the date in the following format: MMDDYY
    filename = os.path.splitext(os.path.basename(filepath))[0] # <--- This will extract the filename without the file-type extension
    parts = filename.split('_') # <--- split the filename ('S1_2_10x' --> ['S1', '2', '10x'])
    prefix = '_'.join(parts[:2]) # <--- get the first two parts of our filename without the microscope zoom information
    result = f"{prefix}_{folder_name}" # <--- join our two pieces of information to get a flake ID
    return result

def open_im_file_dialog(which_image):
    """ A method to open a file dialog to load in an image.

    Args:
        which_image (int): An integer (either 1 or 2) which indicates which image we are loading in with this dialog
    """
    global image_1_path, image_2_path, flake_id
    if(which_image != 1 and which_image != 2): # <--- check to make sure this method is only being called to input image 1 or 2
        raise ValueError("Please enter a value between 1 and 2 inclusive as the image # you're trying to load in")
    file_path = filedialog.askopenfilename(title=f"Select Image {which_image}", filetypes=[("Image files", "*.jpg *.jpeg *.png")]) # <--- Open a file dialog that can take in image files
    if file_path: # <--- if our filepath isn't empty (we have something to process)
        if which_image == 1: # <--- we came here from the Image 1 button
            image_1_path = file_path # <--- Store file path for Image 1
            #print("Selected image 1:", image_1_path) # <--- print statement for debugging
        else: # <--- we came here from the Image 2 button
            image_2_path = file_path # <--- Store file path for Image 2
            #print("Selected image 2:", image_2_path) # <--- print statement for debugging
        flake_id = get_flake_id_from_filepath(file_path)


def push_to_slides(image1_url, image2_url, flake_id='1', nav_instr='1', size='1'):
    """ Method to push gathered information onto google slides.

    Args:
        image1_url (str): The url for the first image to add
        image2_url (str): The url for the second image to add
        flake_id (str, optional): The flake_id for the new slide. Defaults to '1'.
        nav_instr (str, optional): The navigation instructions for the flake on our new slide. Defaults to '1'.
        size (str, optional): The size of the flake on our new slide. Defaults to '1'.
    """
    new_slide_id = duplicate_template_slide() # <--- duplicate the template slide so that we can edit it for our new flake
    presentation_after_duplication = slides_service.presentations().get(presentationId=presentation_id).execute() # <--- pull the new version of the slideshow down with the duplicated slide
    updated_slides = presentation_after_duplication['slides'] # <--- get the list of slides from the new version of the presentation
    last_slide_index = len(updated_slides) # <--- get length of the updated list of slides
    move_slide(new_slide_id, last_slide_index) # <--- move the new slide to the end of the slideshow
    fill_text(new_slide_id, flake_id, size, nav_instr) # <--- update the text on the new slide
    add_images_to_slide(image1_url, image2_url, new_slide_id) # <--- add images to the new slide

def push_to_sheets(flake_id, date, chip_num, flake_num, hmax, vmax, dframes, lframes, layers):
    """ Method to push gathered information onto google sheets.

    Args:
        flake_id (str): The identifier for our flake to add to the sheet.
        date (str): The date of our flake.
        chip_num (int): The chip number of our flake.
        flake_num (int): The flake number of our flake.
        hmax (str): The horizontal max dimension of our flake.
        vmax (str): The vertical max dimension of our flake.
        dframes (str): How many frames down from the top right our flake is.
        lframes (str): How many frames left from the top right our flake is.
        layers (str): How many layers (approximate) our flake is.
    """
    global sheet
    new_row = [flake_id, date, int(chip_num), int(flake_num), float(hmax), float(vmax), float(dframes), float(lframes), layers] # <--- cast each variable to the value it's meant to be and put them in a list to append as the new row in our sheet
    sheet.append_row(new_row) # <--- append the new row we just made

def open_error_window(e):
    """ Method to open up an error window.

    Args:
        e (Exception): The error that caused the program to fail.
    """
    eroot = tk.Toplevel(root) # <--- create a new window
    eroot.title("AN ERROR OCCURED") # <--- give the window a title
    eroot.geometry("400x100") # <--- set the window size

    #Add text to the popup window 
    tk.Label(eroot, text="AN ERROR OCCURED. PLEASE OPEN VSCODE TO INVESTIGATE.", fg='red').pack()
    tk.Label(eroot, text=e, fg='red').pack() # <--- place the error message on the popup window
    print(e)
    eroot.mainloop() # <--- open window

def submit_data():
    """ Method called on push of submit button in GUI, pushes all data entered in GUI onto slides and sheets for a given flake.
    """
    try:
        global flake_id, down_from_TR, left_from_TR, horizontal_max, vertical_max, approx_num_layers, delete_url_list

        #Pull the values from the text entries and parse the flake id to get sample & flake numbers & date
        down_from_TR = entry_down_TR.get()
        left_from_TR = entry_left_TR.get()
        horizontal_max = entry_max_horizontal.get()
        vertical_max = entry_max_vertical.get()
        approx_num_layers = entry_layers.get()


        flake_info = parse_flake_id(flake_id) # <--- parse flake id to get sample, flake numbers & date
        #Extract specifics from flake_info
        date = flake_info['date']
        sample_num = flake_info['chip_num']
        flake_num = flake_info['flake_num']

        formatted_navigation_string = format_navigation_string(float(down_from_TR), float(left_from_TR)) # <--- format the navigation string into plain english from the navigation instruction numbers
        formatted_size_string = f'{horizontal_max} by {vertical_max}' # <--- format size string in plain english

        #Upload images to imgbb and get their urls to use when adding them to slides
        image1_url = upload_image_to_github(image_1_path)
        print(image1_url)
        image2_url = upload_image_to_github(image_2_path)
        print(image2_url)

        # Print out info to debug
        #print("Flake ID:", flake_id)
        #print(f"Chip Number:", sample_num)
        #print(f"Flake Number:", flake_num)
        #print(f"Date Found:", date)
        #print("Max Dimensions:", formatted_size_string)
        #print("Navigation:", formatted_navigation_string)
        #print("10x Image:", image_1_path)
        #print("50x Image:", image_2_path)
        #print("Approximate # Layers:", approx_num_layers)
        
        #Perform the actual upload to sheets and slides
        push_to_sheets(flake_id, date, sample_num, flake_num, horizontal_max, vertical_max, down_from_TR, left_from_TR, approx_num_layers)
        push_to_slides(image1_url, image2_url, flake_id=flake_id, nav_instr=formatted_navigation_string, size=formatted_size_string)


    except (Exception) as e:
        open_error_window(e) # <--- handle any errors by opening up an error popup window
       
def delete_slide(slide_id):
    """Delete the given slide from our presentation.

    Args:
        slide_id (str): The ID of the slide we want to delete from our presentation.
    """
    #Create delete slide request
    delete_request = {
        "requests": [
            {
                "deleteObject": {
                    "objectId": slide_id
                }
            }
        ]
    }
    slides_service.presentations().batchUpdate(presentationId=presentation_id, body=delete_request).execute() # <--- run command to delete slide
   
def delete_last_entry():
    """ Delete the last entry in the slides and sheets.
    """
    all_values = sheet.get_all_values() # <--- load in all rows from the sheet
    last_row = len(all_values) # <--- get the last row

    # Delete it
    if last_row > 1: # <--- if there is more than the header row
        sheet.delete_rows(last_row) # <--- delete the last row
        print(f"Deleted row {last_row}.", 'green') # <--- prints a message confirming successful deletion
    else:
        print("The sheet is empty, cannot delete any rows. Close this window to continue.", 'red') # <--- prints a message showing there were no entries to be deleted 
    
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute() # <--- fetch slides info from drive
    slides = presentation.get('slides') # <--- get list of slides from presentation
    if len(slides) > 1: # <--- check if there are slides (other than the template slide) that we can delete
        #Get ID of last slide
        last_slide = slides[-1]
        slide_id = last_slide['objectId']

        delete_slide(slide_id) # <--- delete last slide
        print(f"Deleted slide with ID: {slide_id}.", 'green') # <--- prints message confirming successful deletion
    else:
       print("No slides found in the presentation. Close this window to continue.", 'red') # <--- prints a message showing there were no slides to be deleted 


env_selector_root = tk.Tk()
env_selector_root.title("Select .env File")
env_selector_root.geometry("600x100")

# Add in env select field

tk.Label(env_selector_root, text="Name of .env File to Use:").pack()
# Initial options
default_env = tk.StringVar()
env_options = load_options("env_filenames.txt")
print(env_options)
print(env_options[0])
default_env.set(env_options[0])
# Combobox widget
env_select = ttk.Combobox(env_selector_root, values=env_options, state="normal", textvariable=default_env, width=40)
env_select.pack()

tk.Button(env_selector_root, text="Next", command=setup_env_info).pack(pady=5)

env_selector_root.mainloop()


pres_id_dict = process_presentation_IDs("Presentation IDs", "Sheet1")



# Create Settings Page
options_root = tk.Tk()
options_root.title("Flake Tracker Settings")
options_root.geometry("600x380")

# Add in presentation ID select field
default_presentation_id = tk.StringVar()
default_presentation_id.set('Default Presentation')
tk.Label(options_root, text="Presentation Name:").pack()
# Initial options
pres_id_options = list(pres_id_dict.keys())
# Combobox widget
presentation_id_select = ttk.Combobox(options_root, values=pres_id_options, state="normal", textvariable=default_presentation_id, width=40)
presentation_id_select.pack()

# Add in spreadsheet select field
default_spreadsheet_name = tk.StringVar()
default_spreadsheet_name.set('Default Sheet')
tk.Label(options_root, text="Spreadsheet Name:").pack()
spreadsheet_options = load_options("spreadsheets.txt")
spreadsheet_select = ttk.Combobox(options_root, values=spreadsheet_options, state="normal", textvariable=default_spreadsheet_name, width=40)
spreadsheet_select.pack()

# Add in sheet name select field
default_sheet_name = tk.StringVar()
default_sheet_name.set('Sheet1')
tk.Label(options_root, text="Sheet Name:").pack()
sheet_options = load_options("sheets.txt")
sheet_select = ttk.Combobox(options_root, values=sheet_options, state="normal", textvariable=default_sheet_name, width=40)
sheet_select.pack()

#Add a button to exit the settings page and use the settings text fields to start up the program
tk.Button(options_root, text="Next", command=shutdown_options_screen).pack(pady=5)

# Open Window
options_root.mainloop()

# GUI setup for main page
root = tk.Tk()
root.title("Flake Tracker")
root.geometry("600x450")

# Text Inputs for main page
tk.Label(root, text="Horizontal Max:").pack()
entry_max_horizontal = tk.Entry(root, width=40)
entry_max_horizontal.pack()

tk.Label(root, text="Vertical Max:").pack()
entry_max_vertical = tk.Entry(root, width=40)
entry_max_vertical.pack()

tk.Label(root, text="Down from Top Right:").pack()
entry_down_TR = tk.Entry(root, width=40)
entry_down_TR.pack()

tk.Label(root, text="Left from Top Right:").pack()
entry_left_TR = tk.Entry(root, width=40)
entry_left_TR.pack()

tk.Label(root, text="Approximate # Layers:").pack()
entry_layers = tk.Entry(root, width=40)
entry_layers.pack()

# File buttons
tk.Button(root, text="Open Image 1", command=lambda: open_im_file_dialog(1)).pack(pady=5)
tk.Button(root, text="Open Image 2", command=lambda: open_im_file_dialog(2)).pack(pady=5)

# Submit button
tk.Button(root, text="Submit", command=submit_data).pack(pady=15)

# Delete last entry button
tk.Button(root, text="Delete Last Entry", command=delete_last_entry).pack(pady=5)

root.mainloop()
