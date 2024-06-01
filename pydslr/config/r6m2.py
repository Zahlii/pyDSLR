# pylint: skip-file
import datetime
from typing import Literal, Optional, Self

import pytz
from pydantic import BaseModel

from pydslr.config.base import BaseConfig


class ActionSettings(BaseModel):
    syncdatetimeutc: Optional[int] = None
    syncdatetime: Optional[int] = None
    uilock: Optional[int] = None
    popupflash: Optional[int] = None
    autofocusdrive: Optional[int] = None
    manualfocusdrive: Optional[Literal["Near 1", "Near 2", "Near 3", "None", "Far 1", "Far 2", "Far 3"]] = None
    cancelautofocus: Optional[int] = None
    eoszoom: Optional[str] = None
    eoszoomposition: Optional[str] = None
    viewfinder: Optional[int] = None
    eosremoterelease: Optional[
        Literal[
            "None",
            "Press Half",
            "Press Full",
            "Release Half",
            "Release Full",
            "Immediate",
            "Press 1",
            "Press 2",
            "Press 3",
            "Release 1",
            "Release 2",
            "Release 3",
        ]
    ] = None
    eosmoviemode: Optional[int] = None
    opcode: Optional[str] = None


class Settings(BaseModel):
    datetimeutc: Optional[int] = None
    datetime: Optional[int] = None
    output: Optional[
        Literal[
            "Off",
            "TFT",
            "PC",
            "TFT + PC",
            "MOBILE",
            "TFT + MOBILE",
            "PC + MOBILE",
            "TFT + PC + MOBILE",
            "MOBILE2",
            "TFT + MOBILE2",
            "PC + MOBILE2",
            "TFT + PC + MOBILE2",
        ]
    ] = None
    movierecordtarget: Optional[Literal["Card", "None", "SDRAM"]] = None
    evfmode: Optional[Literal["1"]] = None
    ownername: Optional[str] = None
    artist: Optional[str] = None
    copyright: Optional[str] = None
    nickname: Optional[str] = None
    customfuncex: Optional[str] = None
    focusarea: Optional[str] = None
    strobofiring: Optional[Literal["1"]] = None
    flashcharged: Optional[str] = None
    oneshotrawon: Optional[str] = None
    autopoweroff: Optional[Literal["15", "30", "60", "180", "300", "600", "1800", "0", "4294967295"]] = None
    depthoffield: Optional[str] = None
    capturetarget: Optional[Literal["Internal RAM", "Memory card"]] = None
    capture: Optional[int] = None
    remotemode: Optional[str] = None
    eventmode: Optional[str] = None
    testolc: Optional[int] = None


class Status(BaseModel):
    serialnumber: Optional[str] = None
    manufacturer: Optional[str] = None
    cameramodel: Optional[str] = None
    deviceversion: Optional[str] = None
    vendorextension: Optional[str] = None
    model: Optional[str] = None
    batterylevel: Optional[str] = None
    mirrorlockstatus: Optional[str] = None
    mirrordownstatus: Optional[str] = None
    lensname: Optional[str] = None
    eosserialnumber: Optional[str] = None
    availableshots: Optional[str] = None
    eosmovieswitch: Optional[str] = None


class ImageSettings(BaseModel):
    imageformat: Optional[
        Literal[
            "Large Fine JPEG",
            "Large Normal JPEG",
            "Medium Fine JPEG",
            "Medium Normal JPEG",
            "Small Fine JPEG",
            "Small Normal JPEG",
            "Smaller JPEG",
            "cRAW + Large Fine JPEG",
            "cRAW + Large Normal JPEG",
            "RAW + Large Fine JPEG",
            "RAW + Large Normal JPEG",
            "cRAW + Medium Fine JPEG",
            "cRAW + Medium Normal JPEG",
            "RAW + Medium Fine JPEG",
            "RAW + Medium Normal JPEG",
            "cRAW + Small Fine JPEG",
            "cRAW + Small Normal JPEG",
            "RAW + Small Fine JPEG",
            "RAW + Small Normal JPEG",
            "cRAW + Smaller JPEG",
            "RAW + Smaller JPEG",
            "RAW",
            "cRAW",
        ]
    ] = None
    imageformatsd: Optional[
        Literal[
            "Large Fine JPEG",
            "Large Normal JPEG",
            "Medium Fine JPEG",
            "Medium Normal JPEG",
            "Small Fine JPEG",
            "Small Normal JPEG",
            "Smaller JPEG",
            "cRAW + Large Fine JPEG",
            "cRAW + Large Normal JPEG",
            "RAW + Large Fine JPEG",
            "RAW + Large Normal JPEG",
            "cRAW + Medium Fine JPEG",
            "cRAW + Medium Normal JPEG",
            "RAW + Medium Fine JPEG",
            "RAW + Medium Normal JPEG",
            "cRAW + Small Fine JPEG",
            "cRAW + Small Normal JPEG",
            "RAW + Small Fine JPEG",
            "RAW + Small Normal JPEG",
            "cRAW + Smaller JPEG",
            "RAW + Smaller JPEG",
            "RAW",
            "cRAW",
        ]
    ] = None
    imageformatcf: Optional[
        Literal[
            "Large Fine JPEG",
            "Large Normal JPEG",
            "Medium Fine JPEG",
            "Medium Normal JPEG",
            "Small Fine JPEG",
            "Small Normal JPEG",
            "Smaller JPEG",
            "cRAW + Large Fine JPEG",
            "cRAW + Large Normal JPEG",
            "RAW + Large Fine JPEG",
            "RAW + Large Normal JPEG",
            "cRAW + Medium Fine JPEG",
            "cRAW + Medium Normal JPEG",
            "RAW + Medium Fine JPEG",
            "RAW + Medium Normal JPEG",
            "cRAW + Small Fine JPEG",
            "cRAW + Small Normal JPEG",
            "RAW + Small Fine JPEG",
            "RAW + Small Normal JPEG",
            "cRAW + Smaller JPEG",
            "RAW + Smaller JPEG",
            "RAW",
            "cRAW",
        ]
    ] = None
    iso: Optional[
        Literal[
            "Auto",
            "100",
            "125",
            "160",
            "200",
            "250",
            "320",
            "400",
            "500",
            "640",
            "800",
            "1000",
            "1250",
            "1600",
            "2000",
            "2500",
            "3200",
            "4000",
            "5000",
            "6400",
            "8000",
            "10000",
            "12800",
            "16000",
            "20000",
            "25600",
            "32000",
            "40000",
            "51200",
        ]
    ] = None
    whitebalance: Optional[
        Literal[
            "Auto",
            "Daylight",
            "Shadow",
            "Cloudy",
            "Tungsten",
            "Fluorescent",
            "Flash",
            "Manual",
            "Color Temperature",
            "AWB White",
        ]
    ] = None
    colortemperature: Optional[
        Literal[
            "2500",
            "2600",
            "2700",
            "2800",
            "2900",
            "3000",
            "3100",
            "3200",
            "3300",
            "3400",
            "3500",
            "3600",
            "3700",
            "3800",
            "3900",
            "4000",
            "4100",
            "4200",
            "4300",
            "4400",
            "4500",
            "4600",
            "4700",
            "4800",
            "4900",
            "5000",
            "5100",
            "5200",
            "5300",
            "5400",
            "5500",
            "5600",
            "5700",
            "5800",
            "5900",
            "6000",
            "6100",
            "6200",
            "6300",
            "6400",
            "6500",
            "6600",
            "6700",
            "6800",
            "6900",
            "7000",
            "7100",
            "7200",
            "7300",
            "7400",
            "7500",
            "7600",
            "7700",
            "7800",
            "7900",
            "8000",
            "8100",
            "8200",
            "8300",
            "8400",
            "8500",
            "8600",
            "8700",
            "8800",
            "8900",
            "9000",
            "9100",
            "9200",
            "9300",
            "9400",
            "9500",
            "9600",
            "9700",
            "9800",
            "9900",
            "10000",
        ]
    ] = None
    whitebalanceadjusta: Optional[
        Literal[
            "-9",
            "-8",
            "-7",
            "-6",
            "-5",
            "-4",
            "-3",
            "-2",
            "-1",
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        ]
    ] = None
    whitebalanceadjustb: Optional[
        Literal[
            "-9",
            "-8",
            "-7",
            "-6",
            "-5",
            "-4",
            "-3",
            "-2",
            "-1",
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        ]
    ] = None
    whitebalancexa: Optional[Literal["0", "1", "2", "3"]] = None
    whitebalancexb: Optional[Literal["0", "1", "2", "3"]] = None
    colorspace: Optional[Literal["sRGB", "AdobeRGB"]] = None


class CaptureSettings(BaseModel):
    zoomspeed: Optional[str] = None
    exposurecompensation: Optional[
        Literal[
            "-3",
            "-2.6",
            "-2.3",
            "-2",
            "-1.6",
            "-1.3",
            "-1",
            "-0.6",
            "-0.3",
            "0",
            "0.3",
            "0.6",
            "1",
            "1.3",
            "1.6",
            "2",
            "2.3",
            "2.6",
            "3",
        ]
    ] = None
    focusmode: Optional[Literal["One Shot", "AI Servo", "AI Focus", "Manual"]] = None
    continuousaf: Optional[Literal["Off", "On"]] = None
    aspectratio: Optional[Literal["3:2", "1:1", "4:3", "16:9", "1.6x"]] = None
    afmethod: Optional[
        Literal[
            "LiveSpotAF",
            "Live",
            "LiveSingleExpandCross",
            "LiveSingleExpandSurround",
            "Unknown value 000c",
            "Unknown value 000e",
        ]
    ] = None
    storageid: Optional[str] = None
    highisonr: Optional[Literal["Off", "Low", "Normal", "High"]] = None
    autoexposuremode: Optional[
        Literal[
            "P",
            "TV",
            "AV",
            "Manual",
            "Bulb",
            "A_DEP",
            "DEP",
            "Custom",
            "Lock",
            "Green",
            "Night Portrait",
            "Sports",
            "Portrait",
            "Landscape",
            "Closeup",
            "Flash Off",
            "C2",
            "C3",
            "Creative Auto",
            "Movie",
            "Auto",
            "Handheld Night Scene",
            "HDR Backlight Control",
            "SCN",
            "Food",
            "Grainy B/W",
            "Soft focus",
            "Toy camera effect",
            "Fish-eye effect",
            "Water painting effect",
            "Miniature effect",
            "HDR art standard",
            "HDR art vivid",
            "HDR art bold",
            "HDR art embossed",
            "Panning",
            "HDR",
            "Self Portrait",
            "Hybrid Auto",
            "Smooth skin",
            "Fv",
        ]
    ] = None
    autoexposuremodedial: Optional[Literal["Fv", "TV", "AV", "Manual", "Bulb"]] = None
    drivemode: Optional[
        Literal[
            "Single",
            "Super high speed continuous shooting",
            "Continuous high speed",
            "Continuous low speed",
            "Timer 10 sec",
            "Timer 2 sec",
            "Continuous timer",
        ]
    ] = None
    picturestyle: Optional[
        Literal[
            "Standard",
            "Portrait",
            "Landscape",
            "Neutral",
            "Faithful",
            "Monochrome",
            "Auto",
            "Fine detail",
            "User defined 1",
            "User defined 2",
            "User defined 3",
        ]
    ] = None
    # 00ff = Auto
    aperture: Optional[
        Literal[
            "Unknown value 00ff",
            "2.8",
            "3.2",
            "3.5",
            "4",
            "4.5",
            "5",
            "5.6",
            "6.3",
            "7.1",
            "8",
            "9",
            "10",
            "11",
            "13",
            "14",
            "16",
            "18",
            "20",
            "22",
        ]
    ] = None
    # actually, bulb means "Auto"
    shutterspeed: Optional[
        Literal[
            "auto",
            "bulb",
            "30",
            "25",
            "20",
            "15",
            "13",
            "10.3",
            "8",
            "6.3",
            "5",
            "4",
            "3.2",
            "2.5",
            "2",
            "1.6",
            "1.3",
            "1",
            "0.8",
            "0.6",
            "0.5",
            "0.4",
            "0.3",
            "1/4",
            "1/5",
            "1/6",
            "1/8",
            "1/10",
            "1/13",
            "1/15",
            "1/20",
            "1/25",
            "1/30",
            "1/40",
            "1/50",
            "1/60",
            "1/80",
            "1/100",
            "1/125",
            "1/160",
            "1/200",
            "1/250",
            "1/320",
            "1/400",
            "1/500",
            "1/640",
            "1/800",
            "1/1000",
            "1/1250",
            "1/1600",
            "1/2000",
            "1/2500",
            "1/3200",
            "1/4000",
            "1/5000",
            "1/6400",
            "1/8000",
        ]
    ] = None
    meteringmode: Optional[Literal["Spot", "Evaluative", "Partial", "Center-weighted average"]] = None
    liveviewsize: Optional[Literal["Large", "Medium", "Small", "val 1"]] = None
    bracketmode: Optional[Literal["Unknown value 0000"]] = None
    aeb: Optional[
        Literal[
            "off",
            "+/- 1/3",
            "+/- 2/3",
            "+/- 1",
            "+/- 1 1/3",
            "+/- 1 2/3",
            "+/- 2",
            "+/- 2 1/3",
            "+/- 2 2/3",
            "+/- 3",
        ]
    ] = None
    alomode: Optional[Literal["Standard (disabled in manual exposure)", "x1", "x2", "x3"]] = None
    movieservoaf: Optional[Literal["Off", "On"]] = None


class R6M2Config(BaseConfig):
    def press_shutter(self) -> Self:
        copied = self.model_copy(deep=True)
        if copied.actions is None:
            copied.actions = ActionSettings()
        copied.actions.eosremoterelease = "Press Full"
        return copied

    def focus_step(self, distance: int) -> Self:
        copied = self.model_copy(deep=True)
        if copied.actions is None:
            copied.actions = ActionSettings()
        if distance == 1:
            copied.actions.manualfocusdrive = "Far 1"
        elif distance == 2:
            copied.actions.manualfocusdrive = "Far 2"
        else:
            copied.actions.manualfocusdrive = "Far 3"
        return copied

    def release_shutter(self) -> Self:
        copied = self.model_copy(deep=True)
        if copied.actions is None:
            copied.actions = ActionSettings()
        copied.actions.eosremoterelease = "Release Full"
        return copied

    def get_camera_time(self) -> Optional[datetime.datetime]:
        if self.settings is None or self.settings.datetimeutc is None:
            return None
        return pytz.utc.localize(datetime.datetime.fromtimestamp(self.settings.datetimeutc))

    def is_raw(self) -> bool:
        return self.imgsettings is not None and self.imgsettings.imageformat is not None and "RAW" in self.imgsettings.imageformat

    def is_sdcard_capture_enabled(self):
        return "card" in self.settings.capturetarget.lower()

    def get_sd_root_folder(self) -> str:
        return "/store_00010001/DCIM/100EOSR6"

    actions: Optional[ActionSettings] = None
    settings: Optional[Settings] = None
    status: Optional[Status] = None
    imgsettings: Optional[ImageSettings] = None
    capturesettings: Optional[CaptureSettings] = None
