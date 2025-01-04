from streetview import search_panoramas
from streetview import get_panorama
from PIL import Image
import requests
import xml.etree.ElementTree as ET
import sys,os.path,glob
import numpy as np

target_lat = "" #latitude here
target_lon = "" #longitude here
target_radius="150" #radius in meters
target_date="2009"

cleanmode = False #cleanmode is true if target directory is completely empty

done_pano_ids = []
done_coords = []

def autocrop(pilImg, threshold = 0): # https://stackoverflow.com/a/30540322
    image = np.array(pilImg)
    """Crops any edges below or equal to threshold

    Crops blank image to 1x1.

    Returns cropped image.

    """
    if len(image.shape) == 3:
        flatImage = np.max(image, 2)
    else:
        flatImage = image
    assert len(flatImage.shape) == 2

    rows = np.where(np.max(flatImage, 0) > threshold)[0]
    if rows.size:
        cols = np.where(np.max(flatImage, 1) > threshold)[0]
        image = image[cols[0]: cols[-1] + 1, rows[0]: rows[-1] + 1]
    else:
        image = image[:1, :1]

    return Image.fromarray(image)

def find_and_save(lat: str, lon: str): 
    panos = search_panoramas(lat,lon)
    global target_date
    for pano in panos:
        if pano.date is not None:
            if target_date in pano.date:
                print(pano)
                global done_pano_ids
                if not cleanmode:
                    if glob.glob(f"output/*{pano.pano_id}.jpg"):
                        print("Aborting this one, already saved this.")
                        return 0
                if pano.pano_id in done_pano_ids:
                    print("Aborting this one, already saved this.")
                    return 0
                done_pano_ids.append(pano.pano_id)
                if not os.path.exists("output/"):
                    os.makedirs("output/")
                if not os.path.isfile(f"output/{lat}~{lon}~{pano.date}~{pano.pano_id}.jpg"):
                    print("Saving this image...")
                    image = get_panorama(pano_id=pano.pano_id)
                    imagecropped = autocrop(image)
                    imagecropped.save(f"output/{lat}~{lon}~{pano.date}~{pano.pano_id}.jpg", "jpeg")
                    return 0
    return 1

def main():
    global cleanmode
    global target_lat
    global target_lon
    global target_radius
    requestxml= f"""<query type=\"way\">
        <around lat=\"{target_lat}\" lon=\"{target_lon}\" radius=\"{target_radius}\"/>
    </query>
    <union>
        <item/>
        <recurse type=\"down\"/>
    </union>
    <print/>"""

    returnxml = requests.post("https://overpass-api.de/api/interpreter",data=requestxml).text
    root = ET.fromstringlist(returnxml)
    ways = root.findall("way")
    nodes = root.findall("node")
    for way in ways:
        for child in way:
            if 'k' in child.attrib:
                if 'highway' in child.attrib['k']:
                    if not any(v in child.attrib['v'] for v in ("footway","cycleway", "pedestrian")):
                        nds = way.findall('nd')
                        for nd in nds:
                            element = [element for element in nodes if element.attrib['id'] == nd.attrib['ref']]
                            if not f"{element[0].attrib['lat']}-{element[0].attrib['lon']}" in done_coords:
                                if not cleanmode:
                                    if glob.glob(f"output/{element[0].attrib['lat']}~{element[0].attrib['lon']}*"):
                                        print(f"File with coordinate exists, skipping: {element[0].attrib['lat']}-{element[0].attrib['lon']}")
                                        continue
                                done_coords.append(f"{element[0].attrib['lat']}-{element[0].attrib['lon']}")
                                find_and_save(element[0].attrib['lat'], element[0].attrib['lon'])
                            else:
                                print(f"Already done coordinate, skipping: {element[0].attrib['lat']}-{element[0].attrib['lon']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
