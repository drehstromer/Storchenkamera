from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import FileResponse
from datetime import datetime
from pydantic import BaseModel
from typing import List, Generator
from dataclasses import dataclass, field

import re
import os

path_to_pictures = "..\..\webcam"



class PictureInformation():
    filename = ""
    sort_index: int = field(init=False, repr=False)
    date: str = field(init=False, repr=True)
    time: str = field(init=False, repr=True)
    unix_timestamp: int = field(default=0, init=False, repr=True)
    is_Valid: bool = field(default=False, init = False, repr=True)

    def __init__(self, filename, pathToPictures):
        self.pathToPictures = pathToPictures
        self.filename = filename
        self.unix_timestamp = self.__getUnixTimestampOfPicture()
        if (self.unix_timestamp != 0) :
            self.time =datetime.fromtimestamp(self.unix_timestamp).strftime("%H:%M:%S")
            self.date =datetime.fromtimestamp(self.unix_timestamp).strftime("%Y-%m-%d")
            self.is_Valid = True

    def __getUnixTimestampOfPicture(self):
        match = re.match(r'(\d+\.\d+\.\d+\.\d+)_(\d+)_(\d{8})(\d{6})(\d{3})_(\w+)\.jpg', self.filename)
        if match:
            date = match.group(3)
            time = match.group(4)

            timestampformat = "%Y%m%d%H%M%S"
            parsedTimeStamp = datetime.strptime(date+time, timestampformat)
        
            return int(parsedTimeStamp.timestamp())
        else:
            raise Exception(f"Could not parse filename: {self.filename}")
        
    def getFileName(self):
        return self.filename
    def getFullFilePath(self):
        return os.path.abspath(self.pathToPictures+ "\\" + self.filename)
    def getDate(self):
        return self.date
    def getTime(self):
        return self.time
    def getUnixTimeStamp(self):
        return self.unix_timestamp


class PicturesInFolder():
    
    def __init__(self, pictureFolder: str) -> None:
        self.pictureFolder : str = pictureFolder
        self.pictures : List[PictureInformation] = []

    def __getNumberOfPicturesInFolder(self) -> int:
        return len([1 for x in list(os.scandir(self.pictureFolder)) if x.is_file()])

    def __getNumberOfLoadedPictures(self) -> int:
        return len(self.pictures)
    
    def __checkForNewPictures(self) -> None:
        if self.__getNumberOfLoadedPictures() != self.__getNumberOfPicturesInFolder() or self.__getNumberOfLoadedPictures() == 0:
            self.__loadAllPictures()

    def __loadAllPictures(self) -> None:
        self.deleteAllPictureInformation()
        for file in os.listdir(self.pictureFolder):
            if (file.endswith(".jpg")):
                self.pictures.append(PictureInformation(
                    filename=file,
                    pathToPictures=self.pictureFolder))

    def deleteAllPictureInformation(self) -> None:
        self.pictures = []
 
    def getNewestPicture(self) -> PictureInformation:
        self.__checkForNewPictures()
        return max(self.pictures, key=lambda x: x.unix_timestamp)
    
    def getPicture(self, unix_timeStamp: int) -> PictureInformation | None:
        self.__checkForNewPictures()
        return next((pic for pic in self.pictures if pic.getUnixTimeStamp() == unix_timeStamp), None)
    
    def getAllPictureInformations(self) -> dict:
        self.__checkForNewPictures()
        return (({"file_date": pic.getDate(),"file_time": pic.getTime(), "file_unix": pic.getUnixTimeStamp()} for pic in self.pictures) if not len(self.pictures) == 0 else None)

    def getPictureInformation(self, start : datetime, end : datetime) -> dict:
        self.__checkForNewPictures()
        internallist : list = []
        for pic in self.pictures:
            if pic.getUnixTimeStamp() >= start.timestamp() and pic.getUnixTimeStamp() < end.timestamp():
                internallist.append({"file_date": pic.getDate(),"file_time": pic.getTime(), "file_unix": pic.getUnixTimeStamp()})

        return internallist if not len(self.pictures) == 0  else None

app = FastAPI()
#app.include_router(PictureHandling)


pictures = PicturesInFolder(path_to_pictures)


@app.get("/")
def root():
    return {"greeting":"Hello Phips"}




@app.get("/api/getNewestPicture")
def getNewestPicture():
    newestPicture = pictures.getNewestPicture()

    if newestPicture is not None:
        response = FileResponse(path=newestPicture.getFullFilePath())
        response.filename = newestPicture.getFileName()
        response.headers['Cache-Control'] = 'no-cache'
        response.headers["file_date"] = str(newestPicture.getDate())
        response.headers["file_time"] = str(newestPicture.getTime())
        response.headers["file_unix"] = str(newestPicture.getUnixTimeStamp())
        print(newestPicture.getFileName())
        return response
    else:
       raise HTTPException(status_code=404, detail="No Picture found")


@app.get("/api/getAllPictureInformations")
def getAllPictureInformations():
    return pictures.getAllPictureInformations()

@app.get("/api/getPictureInformation")
def getAllPictureInformations(start : datetime, end : datetime):
    return pictures.getPictureInformation(start=start,end=end)

@app.get("/api/getPicture/{unix_timestamp}")
def getPicture(unix_timestamp:int):
    pic = pictures.getPicture(unix_timeStamp=unix_timestamp)
    if pic is not None:
        response = FileResponse(path=pic.getFullFilePath())
        response.filename = pic.getFileName()
        response.headers['Cache-Control'] = 'no-cache'
        response.headers["file_date"] = str(pic.getDate())
        response.headers["file_time"] = str(pic.getTime())
        response.headers["file_unix"] = str(pic.getUnixTimeStamp())
        return response
    else:
       raise HTTPException(status_code=404, detail=f"No Picture found with timestamp: {unix_timestamp}")    
