# %% Import the packages
import numpy as np
from PIL import Image
from time import sleep
from selenium import webdriver
import os, logging , json, cv2, io, requests
from rembg import remove as remove_background

# %% Setup and declare variables 
LOGGER, SESSION = logging.info, requests.Session()
SEARCH_URL = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"
THUMBNAIL_, IMAGES_, LOAD_, REFUSE_ = "img.Q4LuWd", 'img.KAlRDb', "input.mye4qd", "button[aria-label='Tout refuser']"
IMG_SLEEP, OFFSET, SCROLL_SCRIPT, HEADERS = 0.2, 30, "window.scrollTo(0, document.body.scrollHeight);", {'User-Agent': 'Chrome/99.0.4844.84'}
OPTIONS = webdriver.ChromeOptions(); OPTIONS.add_argument("--incognito")
CSS_SELECTOR = webdriver.common.by.By.CSS_SELECTOR

DRIVER = webdriver.Chrome(options=OPTIONS); DRIVER.get(SEARCH_URL.format(q='mane'))
find_elements = lambda string: DRIVER.find_elements(by=CSS_SELECTOR, value=string)
find_elements(REFUSE_)[0].click()

# %% Google Images Scraper
class Scraper:
    """Google Images scraper for a given query"""

    def __init__(self, query:str, path:str='images/dummy/image', nbr_images:int=10, process:bool=True):
        # Create a selenium driver and research the query 
        print(f"Fetching images for the query {query}")
        DRIVER.get(SEARCH_URL.format(q=query))

        image_urls = set()
        self.count, results_start = 0, 0
        folder = os.path.dirname(path)
        os.makedirs(folder) if not os.path.exists(folder) else None

        while True:
            # Scroll the window until posible to have enough images 
            for _ in range(10):
                DRIVER.execute_script(SCROLL_SCRIPT), sleep(0.5)  

            # Get all thumnails results
            thumbnail_results = find_elements(THUMBNAIL_)
            for img in thumbnail_results[results_start:]:
                try: 
                    # Click on the thumbnails and get the url corresponding to the image
                    img.click(); sleep(IMG_SLEEP)
                    url = find_elements(IMAGES_)[0].get_attribute('src')

                    # If the url have not been visited yet download the image 
                    if url not in image_urls:
                        image_urls.add(url)
                        bytes_content = SESSION.get(url, headers=HEADERS).content
                        image = Image.open(io.BytesIO(bytes_content)).convert('RGBA')

                        # Preprocess the downloaded image if needed otherwise save it  
                        output_path=f"./{path}{self.count}.png"
                        if process: preprocess_image(image, output_path)
                        else: image.save(output_path)

                        # If there are as much images as we wanted, stop the iteration
                        self.count += 1
                        if self.count >= nbr_images: return
                except: 
                    continue
            else:
                # If no thumbnail is displayed, try to load new images if possible
                print(f"Found {self.count} images from {len(image_urls)} links, looking for more ...")
                try: sleep(10); find_elements(LOAD_)[0].click()
                except: print(f"No more link"); break  
            results_start = len(thumbnail_results)

# %% Pre-processing an Image
def preprocess_image(image:Image.Image, output_path:str):
    # Get the numpy array corresponding to the PIL Image Object
    image = np.array(image)
    (m,n,p) = image.shape

    # Get the image's background color and fill its edges with it    
    background = np.round(np.mean(image[0], axis=0)).astype('uint8')
    padded = np.full((m+2*OFFSET, n+2*OFFSET, p), background)
    padded[OFFSET:OFFSET+m, OFFSET:OFFSET+n] = image

    # Remove the background (this can take up to 2 seconds and is by far the most resource-intensive)
    image = remove_background(padded)

    # Crop the image by removing its unuseful lines and columns after getting its contours with a canny filter  
    canny = cv2.Canny(image, 30, 30)
    def crop(array):
        nulls = [np.all(elem==0) for elem in array]
        return nulls.index(False), len(array)-1-nulls[::-1].index(False)
    (top,bottom), (left,right) = crop(canny), crop(canny.T)
    image = image[top:bottom, left:right, :3]

    # Flip the shoe vertically if necessary to orient it from left to right
    n = len(canny[0])//2
    if np.mean(canny[:,:n]) < np.mean(canny[:,n:]):
        image = np.flip(image, axis=1)

    # Save the processed image
    Image.fromarray(image).save(output_path)
        
# %% Run the scraping
if __name__ == "__main__":

    # Load the parameters  
    JSON = json.load(open('parameters.json', 'r'))
    DEST, NBR_IMAGES, PROCESS, MODELS, SITES = [JSON[key] for key in ['dest', 'nbr_images', 'process', 'models', 'sites']]

    # Create the destination directory with a log file in it 
    os.makedirs(DEST) if not os.path.exists(DEST) else None
    log_file = f'{DEST}/__logs__.log'
    logging.basicConfig(format=' %(message)s', filename=log_file, filemode='w', level=logging.INFO)

    # For each model, scrape all the shoes' images from the 
    # given sites and save them in the destination folder
    for k, model in enumerate(MODELS):
        nbr_saved_model_img = 0
        LOGGER(f"\nScraping '{model}' ({k+1}/{len(MODELS)}) ...")
        for l, site in enumerate(SITES):
            LOGGER(f'\n -- {site} ({l+1}/{len(SITES)}) ')
            site, model = site.strip(), model.strip()
            query, path = f"site:{site} '{model}'", f"{DEST}/{model}/{site}__"
            counter = Scraper(query, path, NBR_IMAGES, PROCESS).count
            nbr_saved_model_img += counter
            LOGGER(f"{counter}/{NBR_IMAGES} images saved from {site}")
        LOGGER(f"\nDownloaded {nbr_saved_model_img} images of '{model}' ({k+1}/{len(MODELS)})\n")
