import os
import psutil
import numpy as np
import requests
import aiohttp
import asyncio
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image


async def extract_details(chapter, session):
    async with session.get(chapter["url"]) as response:
        print(f'start chapter {str(chapter["chapter"]).zfill(2)}')
		
        i = 0
        temp = 0
        pages = []
        soup = BeautifulSoup(await response.text(), "html.parser")
        for image in soup.find_all("img"):
            try:
                bytes = requests.get(image["src"]).content
                height = Image.open(BytesIO(bytes)).height
                
                if temp < height:
                    i = 1
                    temp = height
                    pages.clear
                elif temp == height:
                    pages.append({
						"page": str(i).zfill(2),
						"bytes": bytes
					})
                    i += 1
            except Exception as e:
                print(f"Une erreur s'est produite : {str(e)}")
                continue
        chapter["pages"] = pages
        
        print(f'end chapter {str(chapter["chapter"]).zfill(2)}')
        return chapter


async def extract_details_task(chapters_for_task):
    async with aiohttp.ClientSession() as session:
        tasks = [
            extract_details(chapter, session)
            for chapter in chapters_for_task
        ]
        return await asyncio.gather(*tasks)


def asyncio_wrapper(chapters_for_task):
    return asyncio.run(extract_details_task(chapters_for_task))



def getChapters(elements):
    chapters = []
    for link in reversed(elements.find_all("a")):
        chapters.append({
            "chapter": link.text.split(" chapter ")[1],
            "url": link["href"]
        })
    return chapters


def saveManga(root, Manga):
    if not(os.path.exists(root)): return
    path = os.path.join(root, "Manga")
    if not(os.path.exists(path)): os.mkdir(path)
    

    path = os.path.join(path, Manga["title"])
    if not(os.path.exists(path)): os.mkdir(path)
    

    for chapter in Manga["chapters"]:
        chapter_path = os.path.join(path, chapter["chapter"])
        if not(os.path.exists(chapter_path)): os.mkdir(chapter_path)
        
        for page in chapter["pages"]:
            image_name = f"{chapter_path}\\{page['page']}.jpg"
            
            with open(image_name, "wb") as f:
                f.write(page["bytes"])
            
            print(f"Image {image_name} téléchargée avec succès.")
    os.startfile(path)



def main(base_url):
    soup = BeautifulSoup(requests.get(base_url).content, "html.parser")
    primary = soup.find(id="primary")
    
    num_cores = cpu_count()
    loop = asyncio.get_event_loop()
    executor = ProcessPoolExecutor(max_workers=num_cores)
    tasks = [
        loop.run_in_executor(executor, asyncio_wrapper, chapters_for_task)
        for chapters_for_task in np.array_split(getChapters(primary.find(class_="su-posts")), num_cores)
    ]
    
    chapters = []
    for sublist in loop.run_until_complete(asyncio.gather(*tasks)):
        chapters.extend(sublist)
    
    Manga = {
        "title": primary.find(class_="entry-title").text.title(),
        "chapters": chapters,
    }
    
    # print(Manga)
    print("Path where the manga will be save:", end=" ")
    path = input()

    saveManga(path, Manga)


# drives = psutil.disk_partitions()
# os.path.abspath(__file__).split("\\")[0]
# drives[-1].device
if __name__ == '__main__':
    main("https://theeminenceinshadowmanga.com/")
